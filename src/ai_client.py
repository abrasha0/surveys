import asyncio
import base64
import json
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from PIL import Image

from config import config
from data_handler import save_cache
from schemas import MedicalSurvey, SurveyGroup, SurveyResult


def _image_to_base64(path: Path) -> str:
    with Image.open(path) as img:
        buffer = BytesIO()
        img.save(buffer, format=img.format or "PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


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

    def build_prompt(self, survey: SurveyGroup) -> list[dict]:
        field_lines = []
        for name, field in MedicalSurvey.model_fields.items():
            if name == "needs_review":
                continue
            origin = getattr(field.annotation, "__origin__", None)
            if origin is not None:
                type_str = str(field.annotation)
            else:
                type_str = field.annotation.__name__ if field.annotation else "str"
            extra = ""
            for meta in field.metadata:
                meta_name = type(meta).__name__
                if meta_name == "Ge":
                    extra += f" (min: {meta.ge})"
                elif meta_name == "Le":
                    extra += f" (max: {meta.le})"
            field_lines.append(f"  - {name}: {type_str}{extra}")

        fields_str = "\n".join(field_lines)

        system_msg = (
            "Jesteś asystentem odczytującym dane z medycznych ankiet papierowych.\n"
            "Otrzymasz 5 zdjęć (stron) ankiety medycznej.\n"
            "Zwróć JSON z następującymi polami:\n"
            f"{fields_str}\n"
            "  - needs_review: dict[str, bool] — dla każdego z powyższych pól (oprócz needs_review) ustaw true jeśli nie jesteś pewien odczytu\n"
            "\n"
            "Odpowiedz wyłącznie w formacie JSON, bez dodatkowego tekstu."
        )

        images_b64 = [_image_to_base64(f) for f in survey.files]

        user_msg = {
            "role": "user",
            "content": "Przeanalizuj strony ankiety i zwróć dane w formacie JSON.",
            "images": images_b64,
        }

        return [
            {"role": "system", "content": system_msg},
            user_msg,
        ]

    async def analyze_survey(self, survey: SurveyGroup) -> SurveyResult:
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                messages = self.build_prompt(survey)

                resp = await self._client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "format": "json",
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                body = resp.json()
                content = body.get("message", {}).get("content", "")

                result_json = json.loads(content)
                survey_data = MedicalSurvey.from_ai_json(result_json)

                total = len(MedicalSurvey.model_fields) - 1
                flagged = sum(1 for v in survey_data.needs_review.values() if v)
                confidence = 1.0 - (flagged / max(total, 1))

                return SurveyResult(
                    raw_response=content,
                    validated_data=survey_data,
                    confidence=round(confidence, 4),
                )

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"Failed after {self.max_retries} retries: {last_error}"
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
