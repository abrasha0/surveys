import asyncio
import base64
import json
import logging
import sys
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from pydantic import ValidationError
from PIL import Image

from config import config
from data_handler import save_cache
from schemas import MedicalSurvey, SurveyGroup, SurveyResult

logger = logging.getLogger(__name__)

_OLLAMA_NUM_CTX = 8192

_PAGE_PROMPTS: dict[int, str] = {
    0: (
        "=== Strona 1 ===\n"
        "Otrzymasz zdjęcie PIERWSZEJ strony papierowej ankiety medycznej.\n"
        "Strona zawiera dwie kolumny pytań numerowanych 1-14: dane demograficzne,\n"
        "aktywność zawodową oraz styl życia (sen, ekran, kofeina).\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON:\n"
        "\n"
        "  - plec: \"Kobieta\" lub \"Mężczyzna\"\n"
        "  - wiek: liczba (np. 23)\n"
        "  - miejsce_zamieszkania: \"Wieś\" | \"Miasto do 50 tys. mieszkańców\" | \"Miasto 50-100 tys. mieszkańców\" | \"Miasto powyżej 100 tys. mieszkańców\"\n"
        "  - stan_cywilny: \"Panna/kawaler\" | \"W związku nieformalnym\" | \"Mężatka/żonaty\"\n"
        "  - forma_zamieszkania: \"Z rodziną\" | \"W wynajmowanym mieszkaniu/pokoju\" | \"Własne mieszkanie\" | \"We własnym mieszkaniu z partnerem\" | \"z partnerem\"\n"
        "  - stopien_studiow: \"Studia I stopnia\" lub \"Studia II stopnia\"\n"
        "  - uczelnia: nazwa uczelni (tekst)\n"
        "  - praca_status: \"Nie\" | \"Tak, w zawodzie medycznym\" | \"Tak, poza zawodem\"\n"
        "  - praca_system: tekst (opis systemu pracy, np. \"Jednozmianowym, 8-godzinnym\", \"Zmianowym, 12-godzinnym\"); jeśli nie pracuje to pusty string\n"
        "  - oddzial: \"\" | \"Przychodnia\" | \"Zabiegowym\" | \"Zachowawczym\" | \"Pracownia\"\n"
        "  - staz_pracy: tekst (np. \"2 lata\", \"6 miesięcy\")\n"
        "  - sen_godziny: \"Poniżej 5 godzin\" | \"5-6 godzin\" | \"7-8 godzin\" | \"Powyżej 8 godzin\"\n"
        "  - ekran_godziny: \"1-3 godziny\" lub \"Powyżej 3 godzin\"\n"
        "  - kofeina: \"Nie\" | \"Tak, 1-2 porcje dziennie\" | \"Tak, 3 lub więcej porcji dziennie\"\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    1: (
        "=== Strona 2 ===\n"
        "Otrzymasz zdjęcie DRUGIEJ strony papierowej ankiety medycznej.\n"
        "Strona zawiera macierz 20 stwierdzeń (numerowanych 1-20) dotyczących odczuć\n"
        "i zachowań w minionym tygodniu (skala CES-D). Dla każdego wiersza zaznaczona\n"
        "jest jedna kolumna spośród czterech: \"Rzadko lub wcale (mniej niż 1 dzień)\",\n"
        "\"Przez niedługi czas (1-2 dni)\", \"Czasem lub przez umiarkowany okres (3-4 dni)\",\n"
        "\"Przeważnie lub cały czas (5-7 dni)\".\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON, każde z jedną z powyższych czterech wartości:\n"
        "\n"
        "  - cesd_przeszkadzaly\n"
        "  - cesd_brak_apetytu\n"
        "  - cesd_chandra\n"
        "  - cesd_tak_samo_dobry\n"
        "  - cesd_ciezko_skoncentrowac\n"
        "  - cesd_przygnebiony\n"
        "  - cesd_wysilek\n"
        "  - cesd_optymistycznie\n"
        "  - cesd_zycie_porazka\n"
        "  - cesd_strach\n"
        "  - cesd_sen_niespokojny\n"
        "  - cesd_szczesliwy\n"
        "  - cesd_mowil_mniej\n"
        "  - cesd_samotny\n"
        "  - cesd_ludzie_nieprzyjazni\n"
        "  - cesd_radosci\n"
        "  - cesd_placzu\n"
        "  - cesd_smutno\n"
        "  - cesd_ludzie_nie_lubia\n"
        "  - cesd_nic_nie_zabrac\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    2: (
        "=== Strona 3 ===\n"
        "Otrzymasz zdjęcie TRZECIEJ strony papierowej ankiety medycznej: Ateńska Skala\n"
        "Bezsenności. Strona zawiera 8 pytań (ponumerowanych 1-8), a odpowiedzią jest\n"
        "JEDNA zakreślona kółkiem opcja tekstowa (może to być zakreślenie całego\n"
        "wiersza/frazy, nie pojedynczego słowa) spośród czterech podanych dla danego pytania.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON:\n"
        "\n"
        "  - zasypianie: \"szybkie\" | \"nieznacznie opóźnione\" | \"opóźnione\" | \"bardzo opóźnione lub bezsenność przez całą noc\"\n"
        "  - budzenie_noc: \"nie występuje\" | \"sporadycznie\" | \"często\" | \"bardzo często lub bezsenność przez całą noc\"\n"
        "  - budzenie_rano: \"o zamierzonej godzinie\" | \"nieznacznie wcześniej\" | \"znacznie wcześniej\" | \"dużo wcześniej lub bezsenność przez całą noc\"\n"
        "  - czas_snu: \"wystarczający\" | \"nieznacznie niewystarczający\" | \"wyraźnie niewystarczający\" | \"całkowicie niewystarczający lub bezsenność przez całą noc\"\n"
        "  - jakosc_snu: \"satysfakcjonująca\" | \"nieznacznie niesatysfakcjonująca\" | \"wyraźnie niesatysfakcjonująca\" | \"całkowicie niesatysfakcjonująca\"\n"
        "  - samopoczucie: \"dobre\" | \"nieznacznie gorsze\" | \"wyraźnie gorsze\" | \"wybitnie gorsze\"\n"
        "  - sprawnosc: \"niezaburzona\" | \"nieznacznie zaburzona\" | \"wyraźnie zaburzona\" | \"wybitnie zaburzona\"\n"
        "  - sennosc: \"nie zdarza się\" | \"nieznaczna\" | \"wyraźna\" | \"bardzo nasilona\"\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    3: (
        "=== Strona 4 ===\n"
        "Otrzymasz zdjęcie CZWARTEJ strony papierowej ankiety medycznej: Skala Zmęczenia\n"
        "(MFIS), pozycje 1-15 z 21 (górna połowa tabeli, strona oznaczona jako \"1/2\").\n"
        "Strona zawiera tabelę: kolumny to \"Nigdy\"=0, \"Rzadko\"=1, \"Czasami\"=2, \"Często\"=3,\n"
        "\"Prawie zawsze\"=4, a odpowiedzią w każdym wierszu jest liczba zakreślona kółkiem.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON, każde jako jedną z wartości:\n"
        "\"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "\n"
        "  - objaw_mniej_uwazna\n"
        "  - objaw_trudno_skupic\n"
        "  - objaw_trudno_myslec\n"
        "  - objaw_niezdarna\n"
        "  - objaw_zapominalska\n"
        "  - objaw_wyznaczac_tempo\n"
        "  - objaw_zmotywowac_fizycznie\n"
        "  - objaw_zmotywowac_spotkania\n"
        "  - objaw_nie_zdolna_poza_domem\n"
        "  - objaw_wysilek_fizyczny\n"
        "  - objaw_trudnosci_decyzyjne\n"
        "  - objaw_zmusic_do_myslenia\n"
        "  - objaw_miesnie_z_waty\n"
        "  - objaw_dyskomfort_fizyczny\n"
        "  - objaw_ukonczenie_myslenie\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    4: (
        "=== Strona 5 ===\n"
        "Otrzymasz zdjęcie PIĄTEJ strony papierowej ankiety medycznej: dokończenie Skali\n"
        "Zmęczenia (MFIS), pozycje 16-21 z 21, oraz krótki blok pytań o stan zdrowia.\n"
        "Tabela MFIS ma te same kolumny co poprzednio: \"Nigdy\"=0, \"Rzadko\"=1, \"Czasami\"=2,\n"
        "\"Często\"=3, \"Prawie zawsze\"=4, odpowiedź to liczba zakreślona kółkiem.\n"
        "Poniżej tabeli znajdują się pytania Tak/Nie o anemię i problemy z tarczycą\n"
        "(zaznaczane krzyżykiem) oraz pole tekstowe na inne choroby.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON:\n"
        "\n"
        "  - objaw_uporzadkowanie_mysli: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "  - objaw_ukonczenie_wysilek: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "  - objaw_myslenie_spowolnione: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "  - objaw_problemy_koncentracja: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "  - objaw_ograniczyc_aktywnosc: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "  - objaw_czesciej_odpoczywac: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
        "\n"
        "  - anemia: \"Tak\" lub \"Nie\"\n"
        "  - problemy_tarczyca: \"Tak\" lub \"Nie\"\n"
        "  - jaka_tarczyca: tekst (jeśli problemy_tarczyca=\"Nie\", to pusty string)\n"
        "  - inne_choroby: tekst lub pusty string\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
}


@dataclass
class ProcessingStatus:
    survey_idx: int
    total_surveys: int
    page_idx: int
    total_pages: int
    status: str
    message: str
    extra: dict[str, Any] | None = None


_PAGE_NAMES: dict[int, str] = {
    0: "Strona 1 \u2013 Demografia + styl \u017cycia",
    1: "Strona 2 \u2013 CES-D",
    2: "Strona 3 \u2013 Ate\u0144ska skala bezsenno\u015bci",
    3: "Strona 4 \u2013 MFIS (1-15)",
    4: "Strona 5 \u2013 MFIS (16-21) + stan zdrowia",
}



def _image_to_base64(path: Path) -> str:
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format=img.format or "JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _merge_partial_results(parts: list[dict]) -> dict:
    merged: dict[str, Any] = {}
    combined_review: dict[str, bool] = {}
    for part in parts:
        review = part.pop("needs_review", {}) or {}
        combined_review.update(review)
        for k, v in part.items():
            merged.setdefault(k, v)
    merged["needs_review"] = combined_review
    return merged


class AIClient:
    def __init__(
        self,
        model_name: str = config.model_name,
        base_url: str = config.ollama_url,
        max_retries: int = config.max_retries,
        timeout_sec: int = config.timeout_sec,
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout_sec = timeout_sec
        self._client = httpx.AsyncClient(timeout=timeout_sec)

    async def close(self):
        await self._client.aclose()

    def _build_page_prompt(self, page_index: int, image_b64: str) -> list[dict]:
        system_prompt = _PAGE_PROMPTS.get(page_index)
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "images": [image_b64],
                "content": "Przeanalizuj zdjęcie i zwróć JSON z polami dla tej strony.",
            },
        ]

    async def check_ollama_health(self) -> dict:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            logger.info(
                "Ollama health OK — %d model(s) loaded: %s",
                len(models), ", ".join(models) if models else "none",
            )
            return data
        except Exception as e:
            logger.warning("Ollama health check failed: %s", e)
            return {}

    async def _analyze_page(
        self, image_path: Path, page_index: int, progress_callback: Callable[[ProcessingStatus], None] | None = None,
        survey_idx: int = 0, total_surveys: int = 1, total_pages: int = 1,
    ) -> dict:
        last_error: Exception | None = None
        prompt_preview = _PAGE_PROMPTS.get(page_index, "")[:200]

        logger.debug(
            "Sending page %d to model '%s': image=%s, prompt=%s...",
            page_index, self.model_name, image_path.name, prompt_preview,
        )

        for attempt in range(self.max_retries):
            t0 = time.perf_counter()
            try:
                if attempt > 0 and progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=page_index, total_pages=total_pages,
                        status="retrying",
                        message=f"Ankieta {survey_idx + 1}, Strona {page_index + 1}: Ponawianie ({attempt + 1}/{self.max_retries})...",
                        extra={"attempt": attempt + 1, "max_retries": self.max_retries},
                    ))

                image_b64 = _image_to_base64(image_path)
                messages = self._build_page_prompt(page_index, image_b64)

                resp = await self._client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "format": "json",
                        "stream": False,
                        "options": {"num_ctx": _OLLAMA_NUM_CTX},
                    },
                )
                elapsed = time.perf_counter() - t0
                resp.raise_for_status()
                body = resp.json()
                content = body.get("message", {}).get("content", "")

                eval_count = body.get("eval_count")
                eval_duration = body.get("eval_duration")
                if eval_count is not None:
                    logger.debug(
                        "Page %d: model returned %d tokens in %.2fs (eval_duration=%s)",
                        page_index, eval_count, elapsed, eval_duration,
                    )

                parsed = json.loads(content)
                response_preview = json.dumps(parsed, ensure_ascii=False)[:500]
                logger.debug(
                    "Model response for page %d (%.2fs): %s",
                    page_index, elapsed, response_preview,
                )

                return parsed

            except Exception as e:
                elapsed = time.perf_counter() - t0
                last_error = e
                logger.warning(
                    "Attempt %d/%d for page %d failed after %.2fs: %s: %s",
                    attempt + 1, self.max_retries, page_index, elapsed,
                    type(e).__name__, str(e)[:300],
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

        raise RuntimeError(
            f"page {page_index} failed after {self.max_retries} retries: {type(last_error).__name__}"
        )

    async def analyze_survey(
        self,
        survey: SurveyGroup,
        survey_idx: int = 0,
        total_surveys: int = 1,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
    ) -> SurveyResult:
        survey_t0 = time.perf_counter()
        good: list[dict] = []
        failed_pages: dict[str, bool] = {}
        total_pages = len(survey.files)

        logger.info("Starting survey %d/%d (%d pages)", survey_idx + 1, total_surveys, total_pages)

        for page_idx, file_path in enumerate(survey.files):
            page_name = _PAGE_NAMES.get(page_idx, f"Strona {page_idx + 1}")

            if progress_callback:
                progress_callback(ProcessingStatus(
                    survey_idx=survey_idx,
                    total_surveys=total_surveys,
                    page_idx=page_idx,
                    total_pages=total_pages,
                    status="processing_page",
                    message=f"Ankieta {survey_idx + 1}, Strona {page_idx + 1}/{total_pages}: Przetwarzanie {page_name}...",
                ))

            try:
                result = await self._analyze_page(
                    file_path, page_idx,
                    progress_callback=progress_callback,
                    survey_idx=survey_idx, total_surveys=total_surveys, total_pages=total_pages,
                )
                good.append(result)
            except Exception:
                failed_pages[f"page_{page_idx}"] = True
                logger.warning("Survey %d page %d failed permanently", survey.id, page_idx)
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx,
                        total_surveys=total_surveys,
                        page_idx=page_idx,
                        total_pages=total_pages,
                        status="page_error",
                        message=f"Ankieta {survey_idx + 1}, Strona {page_idx + 1}/{total_pages}: B\u0142\u0105d - {page_name}",
                    ))

        merged = _merge_partial_results(good)
        merged.setdefault("needs_review", {}).update(failed_pages)

        logger.debug(
            "Survey %d merged result: %d fields, failed_pages=%s",
            survey.id, len(merged), failed_pages,
        )

        try:
            survey_data = MedicalSurvey.from_ai_json(merged)
        except ValidationError as e:
            bad_fields = ", ".join(str(loc) for loc in e.errors()[0]["loc"])
            logger.error("Survey %d validation failed: %s", survey.id, bad_fields)
            raise RuntimeError(
                f"Validation failed for survey {survey.id}: bad field '{bad_fields}' - check AI output"
            ) from e

        total = len(MedicalSurvey.model_fields) - 1
        flagged = sum(1 for v in survey_data.needs_review.values() if v)
        confidence = 1.0 - (flagged / max(total, 1))
        survey_elapsed = time.perf_counter() - survey_t0

        logger.info(
            "Survey %d done in %.1fs — confidence=%.0f%%, flagged=%d/%d",
            survey.id, survey_elapsed, confidence * 100, flagged, total,
        )

        if progress_callback:
            progress_callback(ProcessingStatus(
                survey_idx=survey_idx,
                total_surveys=total_surveys,
                page_idx=-1,
                total_pages=total_pages,
                status="survey_done",
                message=f"Ankieta {survey_idx + 1}/{total_surveys} gotowa (ufno\u015b\u0107: {confidence:.0%})",
                extra={"elapsed_s": round(survey_elapsed, 1), "confidence": round(confidence, 4)},
            ))

        return SurveyResult(
            raw_response=json.dumps(merged, ensure_ascii=False),
            validated_data=survey_data,
            confidence=round(confidence, 4),
        )

    async def analyze_batch(
        self,
        surveys: list[SurveyGroup],
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
    ) -> list[SurveyResult]:
        batch_t0 = time.perf_counter()
        results: dict[int, SurveyResult] = {}
        total = len(surveys)

        logger.info("=" * 50)
        logger.info("Batch start: %d survey(s) to process with model '%s'", total, self.model_name)

        health = await self.check_ollama_health()

        for idx, survey in enumerate(surveys):
            result = await self.analyze_survey(
                survey,
                survey_idx=idx,
                total_surveys=total,
                progress_callback=progress_callback,
            )
            results[survey.id] = result
            save_cache(results)

        batch_elapsed = time.perf_counter() - batch_t0
        avg_confidence = sum(r.confidence for r in results.values()) / max(len(results), 1)

        logger.info(
            "Batch complete: %d/%d surveys processed in %.1fs (avg confidence=%.0f%%)",
            len(results), total, batch_elapsed, avg_confidence * 100,
        )
        logger.info("=" * 50)

        if progress_callback:
            progress_callback(ProcessingStatus(
                survey_idx=total - 1,
                total_surveys=total,
                page_idx=-1,
                total_pages=0,
                status="batch_done",
                message=f"Przetworzono {len(results)}/{total} ankiet w {batch_elapsed:.0f}s",
                extra={"elapsed_s": round(batch_elapsed, 1), "avg_confidence": round(avg_confidence, 4)},
            ))

        return [results[s.id] for s in surveys]
