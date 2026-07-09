import asyncio
import base64
import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from pydantic import ValidationError
from PIL import Image

from config import config
from data_handler import save_cache
from schemas import MedicalSurvey, SurveyGroup, SurveyResult

_OLLAMA_NUM_CTX = 8192

_PAGE_PROMPTS: dict[int, str] = {
    0: (
        "=== Strona 1 ===\n"
        "Otrzymasz zdjęcie pierwszej strony papierowej ankiety medycznej.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON:\n"
        "\n"
        "  - plec: \"Kobieta\" lub \"Mężczyzna\"\n"
        "  - wiek: liczba (np. 23)\n"
        "  - miejsce_zamieszkania: \"Wieś\" | \"Miasto do 50 tys. mieszkańców\" | \"Miasto 50-100 tys. mieszkańców\" | \"Miasto powyżej 100 tys. mieszkańców\"\n"
        "  - stan_cywilny: \"Panna/kawaler\" | \"W związku nieformalnym\" | \"Mężatka/żonaty\"\n"
        "  - forma_zamieszkania: \"Z rodziną\" | \"W wynajmowanym mieszkaniu/pokoju\" | \"Własne mieszkanie\" | \"We własnym mieszkaniu z partnerem\" | \"z partnerem\"\n"
        "  - stopien_studiow: \"Studia I stopnia\" lub \"Studia II stopnia\"\n"
        "  - uczelnia: nazwa uczelni (tekst)\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    1: (
        "=== Strona 2 ===\n"
        "Otrzymasz zdjęcie drugiej strony papierowej ankiety medycznej.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON:\n"
        "\n"
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
    2: (
        "=== Strona 3 ===\n"
        "Otrzymasz zdjęcie trzeciej strony papierowej ankiety medycznej.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON (częstotliwość objawów w ostatnich 4 tygodniach):\n"
        "Każde pole: \"Nigdy\" | \"Rzadko\" | \"Czasami\" | \"Często\" | \"Prawie zawsze\"\n"
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
        "  - objaw_uporzadkowanie_mysli\n"
        "  - objaw_ukonczenie_wysilek\n"
        "  - objaw_myslenie_spowolnione\n"
        "  - objaw_problemy_koncentracja\n"
        "  - objaw_ograniczyc_aktywnosc\n"
        "  - objaw_czesciej_odpoczywac\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    3: (
        "=== Strona 4 ===\n"
        "Otrzymasz zdjęcie czwartej strony papierowej ankiety medycznej.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON:\n"
        "\n"
        "  - anemia: \"Tak\" lub \"Nie\"\n"
        "  - problemy_tarczyca: \"Tak\" lub \"Nie\"\n"
        "  - jaka_tarczyca: tekst (jeśli problemy_tarczyca=\"Nie\", to pusty string)\n"
        "  - inne_choroby: tekst lub pusty string\n"
        "\n"
        "  - zasypianie: \"szybkie\" | \"nieznacznie opóźnione\" | \"opóźnione\" | \"bardzo opóźnione lub bezsenność przez całą noc\"\n"
        "  - budzenie_noc: \"nie występuje\" | \"sporadycznie\" | \"często\" | \"bardzo często lub bezsenność przez całą noc\"\n"
        "  - budzenie_rano: \"o zamierzonej godzinie\" | \"nieznacznie wcześniej\" | \"znacznie wcześniej\" | \"dużo wcześniej lub bezsenność przez całą noc\"\n"
        "  - czas_snu: \"wystarczający\" | \"nieznacznie niewystarczający\" | \"wyraźnie niewystarczający\" | \"całkowicie niewystarczający lub bezsenność przez całą noc\"\n"
        "  - jakosc_snu: \"satysfakcjonująca\" | \"nieznacznie niesatysfakcjonująca\" | \"wyraźnie niesatysfakcjonująca\" | \"całkowicie niesatysfakcjonująca\"\n"
        "  - samopoczucie: \"dobre\" | \"nieznacznie gorsze\" | \"wyraźnie gorsze\"\n"
        "  - sprawnosc: \"niezaburzona\" | \"nieznacznie zaburzona\" | \"wyraźnie zaburzona\"\n"
        "  - sennosc: \"nie zdarza się\" | \"nieznaczna\" | \"wyraźna\" | \"bardzo nasilona\"\n"
        "\n"
        "  - needs_review: dict[str, bool] — dla każdego z powyższych pól ustaw true jeśli nie jesteś pewien odczytu\n"
        "\n"
        "Odpowiedz wyłącznie w formacie JSON."
    ),
    4: (
        "=== Strona 5 ===\n"
        "Otrzymasz zdjęcie piątej strony papierowej ankiety medycznej.\n"
        "Zwróć WYŁĄCZNIE następujące pola JSON (samopoczucie w ostatnim tygodniu, skala CES-D):\n"
        "Każde pole: \"Rzadko lub wcale (mniej niż 1 dzień)\" | \"Przez niedługi czas (1-2 dni)\" | \"Czasem lub przez umiarkowany okres (3-4 dni)\" | \"Przeważnie lub cały czas (5-7 dni)\"\n"
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

    async def _analyze_page(
        self, image_path: Path, page_index: int
    ) -> dict:
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
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
                resp.raise_for_status()
                body = resp.json()
                content = body.get("message", {}).get("content", "")

                return json.loads(content)

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

        raise RuntimeError(
            f"page {page_index} failed after {self.max_retries} retries: {type(last_error).__name__}"
        )

    async def analyze_survey(self, survey: SurveyGroup) -> SurveyResult:
        page_tasks = [
            self._analyze_page(file_path, idx)
            for idx, file_path in enumerate(survey.files)
        ]
        raw_parts = await asyncio.gather(*page_tasks, return_exceptions=True)

        good: list[dict] = []
        failed_pages: dict[str, bool] = {}
        for idx, part in enumerate(raw_parts):
            if isinstance(part, Exception):
                failed_pages[f"page_{idx}"] = True
            else:
                good.append(part)

        merged = _merge_partial_results(good)
        merged.setdefault("needs_review", {}).update(failed_pages)

        try:
            survey_data = MedicalSurvey.from_ai_json(merged)
        except ValidationError as e:
            bad_fields = ", ".join(e.errors()[0]["loc"])
            raise RuntimeError(
                f"Validation failed for survey {survey.id}: bad field '{bad_fields}' - check AI output"
            ) from e

        total = len(MedicalSurvey.model_fields) - 1
        flagged = sum(1 for v in survey_data.needs_review.values() if v)
        confidence = 1.0 - (flagged / max(total, 1))

        return SurveyResult(
            raw_response=json.dumps(merged, ensure_ascii=False),
            validated_data=survey_data,
            confidence=round(confidence, 4),
        )

    async def analyze_batch(
        self,
        surveys: list[SurveyGroup],
        progress_callback=None,
    ) -> list[SurveyResult]:
        semaphore = asyncio.Semaphore(2)
        results: dict[int, SurveyResult] = {}
        total = len(surveys)

        async def _process(survey: SurveyGroup) -> tuple[int, SurveyResult]:
            async with semaphore:
                result = await self.analyze_survey(survey)
                return survey.id, result

        tasks = [_process(s) for s in surveys]
        completed = 0

        for coro in asyncio.as_completed(tasks):
            sid, result = await coro
            results[sid] = result
            completed += 1
            save_cache(results)
            if progress_callback:
                progress_callback(completed, total)

        return [results[s.id] for s in surveys]
