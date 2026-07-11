import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import httpx
from PIL import Image, ImageEnhance

from config import config
from domain.schemas import MedicalSurvey
from ai.prompts import build_system_prompt
from domain.field_specs import ALL_FIELDS

logger = logging.getLogger(__name__)

_OLLAMA_NUM_CTX = 8192
_OLLAMA_TEMPERATURE = 0.0
_OLLAMA_KEEP_ALIVE = "-1"
_MAX_IMAGE_DIMENSION = 2000
_CONTRAST_FACTOR = 1.5

@dataclass
class ProcessingStatus:
    survey_idx: int
    total_surveys: int
    page_idx: int
    total_pages: int
    status: str          # "processing_page", "retrying", "page_error", "survey_done", "batch_done"
    message: str
    extra: dict[str, Any] | None = None


def preprocess_image(path: Path) -> bytes:
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        w, h = img.size
        long_side = max(w, h)
        if long_side > _MAX_IMAGE_DIMENSION:
            scale = _MAX_IMAGE_DIMENSION / long_side
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(_CONTRAST_FACTOR)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def _image_to_base64(path: Path) -> str:
    raw = preprocess_image(path)
    return base64.b64encode(raw).decode("utf-8")


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

    async def check_ollama_health(self) -> dict:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            logger.info("Ollama health OK – %d model(s)", len(models))
            return data
        except Exception as e:
            logger.warning("Ollama health check failed: %s", e)
            return {}

    async def _analyze_page(
        self,
        image_path: Path,
        page_index: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
        survey_idx: int = 0,
        total_surveys: int = 1,
        total_pages: int = 1,
    ) -> dict:
        last_error = None
        system_prompt = build_system_prompt(page_index)

        for attempt in range(self.max_retries):
            t0 = time.perf_counter()
            try:
                if attempt > 0 and progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx,
                        total_surveys=total_surveys,
                        page_idx=page_index,
                        total_pages=total_pages,
                        status="retrying",
                        message=f"Ankieta {survey_idx+1}, Strona {page_index+1}: Ponawianie ({attempt+1}/{self.max_retries})...",
                        extra={"attempt": attempt+1, "max_retries": self.max_retries},
                    ))

                image_b64 = _image_to_base64(image_path)
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "images": [image_b64], "content": "Przeanalizuj zdjęcie i zwróć JSON."},
                ]

                resp = await self._client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "format": "json",
                        "stream": False,
                        "keep_alive": _OLLAMA_KEEP_ALIVE,
                        "options": {
                            "num_ctx": _OLLAMA_NUM_CTX,
                            "temperature": _OLLAMA_TEMPERATURE,
                        },
                    },
                )
                elapsed = time.perf_counter() - t0
                resp.raise_for_status()
                body = resp.json()
                content = body.get("message", {}).get("content", "")
                parsed = json.loads(content)
                logger.debug("Page %d parsed in %.2fs", page_index, elapsed)
                return parsed

            except Exception as e:
                elapsed = time.perf_counter() - t0
                last_error = e
                logger.warning(
                    "Attempt %d/%d for page %d failed after %.2fs: %s",
                    attempt+1, self.max_retries, page_index, elapsed, str(e)[:200],
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"Page {page_index} failed after {self.max_retries} retries")

    async def analyze_survey(
        self,
        survey_files: list[Path],
        survey_idx: int,
        total_surveys: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
    ) -> dict:
        """Zwraca słownik ze scalonymi danymi ankiety."""
        total_pages = len(survey_files)
        page_results = []
        for page_idx, file_path in enumerate(survey_files):
            if progress_callback:
                progress_callback(ProcessingStatus(
                    survey_idx=survey_idx,
                    total_surveys=total_surveys,
                    page_idx=page_idx,
                    total_pages=total_pages,
                    status="processing_page",
                    message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}/{total_pages}: przetwarzanie...",
                ))
            try:
                result = await self._analyze_page(
                    file_path, page_idx,
                    progress_callback=progress_callback,
                    survey_idx=survey_idx,
                    total_surveys=total_surveys,
                    total_pages=total_pages,
                )
                page_results.append(result)
            except Exception as e:
                logger.error("Survey %d page %d error: %s", survey_idx, page_idx, e)
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx,
                        total_surveys=total_surveys,
                        page_idx=page_idx,
                        total_pages=total_pages,
                        status="page_error",
                        message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: błąd – pominięto",
                    ))
                # Wstaw pusty słownik, by nie psuć scalania
                page_results.append({})

        # Scalanie
        merged = {}
        needs_review = {}
        for part in page_results:
            if not part:
                continue
            review = part.pop("needs_review", {}) or {}
            needs_review.update(review)
            for k, v in part.items():
                if v is not None:
                    merged.setdefault(k, v)
        merged["needs_review"] = needs_review

        # Walidacja
        try:
            validated = MedicalSurvey.from_ai_json(merged)
        except Exception as e:
            logger.error("Validation failed for survey %d: %s", survey_idx, e)
            raise

        # Konwersja na dict z danymi i needs_review
        result_dict = validated.model_dump()
        result_dict["needs_review"] = validated.needs_review
        return result_dict

    async def analyze_batch(
        self,
        survey_groups: list[list[Path]],
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
        survey_done_callback: Callable[[int, dict], None] | None = None,  # survey_idx, result_dict
    ) -> list[dict]:
        """Przetwarza wszystkie grupy, wywołując callback po każdej ankiecie."""
        total = len(survey_groups)
        results = []
        for idx, files in enumerate(survey_groups):
            try:
                result_dict = await self.analyze_survey(
                    files, idx, total, progress_callback
                )
                results.append(result_dict)
                if survey_done_callback:
                    survey_done_callback(idx, result_dict)
            except Exception as e:
                logger.error("Survey %d failed: %s", idx, e)
                # Można dodać pusty wynik z błędem
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=idx,
                        total_surveys=total,
                        page_idx=-1,
                        total_pages=0,
                        status="survey_error",
                        message=f"Ankieta {idx+1} – błąd krytyczny: {str(e)[:100]}",
                    ))
                # Dodajemy pusty słownik, żeby zachować indeksy
                results.append({})
        return results