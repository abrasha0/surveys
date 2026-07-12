import asyncio
import base64
import json
import logging
import time
from contextlib import asynccontextmanager, nullcontext
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import httpx
from PIL import Image, ImageEnhance

from config import config
from domain.schemas import MedicalSurvey
from ai.prompts import build_vlm_prompt, build_text_format_prompt
from domain.field_specs import ALL_FIELDS
from logger import ai_req_logger

try:
    from ai.tracing import vlm_trace, llm_trace, io_trace, TraceContext
    _HAS_TRACING = True
except ImportError:
    _HAS_TRACING = False

logger = logging.getLogger(__name__)

_OLLAMA_NUM_CTX = config.ai["num_ctx"]
_OLLAMA_TEMPERATURE = config.ai["temperature"]
_OLLAMA_KEEP_ALIVE = config.ai["keep_alive"]
_MAX_IMAGE_DIMENSION = config.image["max_dimension"]
_CONTRAST_FACTOR = config.image["contrast_factor"]


@asynccontextmanager
async def log_ai_call(operation: str, model: str, page_idx: int, survey_idx: int, **extra):
    t0 = time.perf_counter()
    extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
    header = f"{operation} | model={model} | page={page_idx} | survey={survey_idx}"
    if extra_str:
        header += f" | {extra_str}"
    if ai_req_logger:
        ai_req_logger.info("%s", header)
    try:
        yield
    except Exception as e:
        elapsed = time.perf_counter() - t0
        if ai_req_logger:
            ai_req_logger.error(
                "%s_err | model=%s | page=%d | latency=%.2fs | error_type=%s | error=%s",
                operation, model, page_idx, elapsed, type(e).__name__, str(e)[:300],
            )
        raise
    else:
        elapsed = time.perf_counter() - t0
        if ai_req_logger:
            ai_req_logger.info(
                "%s_ok | model=%s | page=%d | latency=%.2fs",
                operation, model, page_idx, elapsed,
            )

@dataclass
class ProcessingStatus:
    survey_idx: int
    total_surveys: int
    page_idx: int
    total_pages: int
    status: str          # "survey_start", "vlm_extracting", "vlm_retrying", "text_formatting", "text_retrying",
                         # "fallback_activated", "page_error", "survey_done", "batch_done", "survey_error"
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
        img.save(buf, format="JPEG", quality=config.image["jpeg_quality"])
        return buf.getvalue()


def _image_to_base64(path: Path) -> str:
    raw = preprocess_image(path)
    return base64.b64encode(raw).decode("utf-8")


class AIClient:
    def __init__(
        self,
        vlm_model: str = config.ai["vlm_model"],
        text_model: str = config.ai["text_model"],
        base_url: str = config.ai["ollama_url"],
        max_retries: int = config.ai["max_retries"],
        timeout_sec: int = config.ai["timeout_sec"],
    ):
        self.vlm_model = vlm_model
        self.text_model = text_model
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

    async def _extract_text_vlm(
        self,
        image_path: Path,
        page_index: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
        survey_idx: int = 0,
        total_surveys: int = 1,
        total_pages: int = 1,
    ) -> str:
        last_error = None
        system_prompt = build_vlm_prompt(page_index)

        ctx = TraceContext(
            operation="extract_text",
            model=self.vlm_model,
            page_idx=page_index,
            survey_idx=survey_idx,
        ) if _HAS_TRACING else None

        async with (vlm_trace(ctx) if ctx else nullcontext()):
            for attempt in range(self.max_retries):
                t0 = time.perf_counter()
                try:
                    if progress_callback:
                        progress_callback(ProcessingStatus(
                            survey_idx=survey_idx,
                            total_surveys=total_surveys,
                            page_idx=page_index,
                            total_pages=total_pages,
                            status="vlm_extracting" if attempt == 0 else "vlm_retrying",
                            message=f"Ankieta {survey_idx+1}, Strona {page_index+1}/{total_pages}: VLM ekstrakcja tekstu..." if attempt == 0
                                    else f"Ankieta {survey_idx+1}, Strona {page_index+1}: VLM ponawianie ({attempt+1}/{self.max_retries})...",
                        ))

                    if _HAS_TRACING:
                        async with io_trace("image_base64", {"page_idx": page_index, "path": str(image_path)}):
                            image_b64 = _image_to_base64(image_path)
                    else:
                        image_b64 = _image_to_base64(image_path)

                    if ai_req_logger:
                        ai_req_logger.info(
                            "vlm_extract | model=%s | page=%d | survey=%d | attempt=%d/%d | prompt_preview=%s",
                            self.vlm_model, page_index, survey_idx, attempt+1, self.max_retries,
                            system_prompt[:200],
                        )
                    resp = await self._client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.vlm_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "images": [image_b64], "content": "Przeanalizuj zdjęcie i wyekstrahuj tekst."},
                            ],
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
                    raw_text = body.get("message", {}).get("content", "")
                    if ai_req_logger:
                        ai_req_logger.info(
                            "vlm_extract_ok | model=%s | page=%d | chars=%d | latency=%.2fs",
                            self.vlm_model, page_index, len(raw_text), elapsed,
                        )
                    logger.info("VLM page %d extracted %d chars in %.2fs", page_index, len(raw_text), elapsed)
                    return raw_text

                except httpx.HTTPStatusError as hse:
                    elapsed = time.perf_counter() - t0
                    last_error = hse
                    logger.warning(
                        "VLM HTTP %d page %d attempt %d/%d after %.2fs: %s",
                        hse.response.status_code, page_index, attempt+1, self.max_retries, elapsed,
                        hse.response.text[:500],
                    )
                    if ai_req_logger:
                        ai_req_logger.error(
                            "vlm_extract_err | model=%s | page=%d | attempt=%d/%d | error_type=HTTPStatusError | http_status=%d | error=%s",
                            self.vlm_model, page_index, attempt+1, self.max_retries,
                            hse.response.status_code, hse.response.text[:300],
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

                except Exception as e:
                    elapsed = time.perf_counter() - t0
                    last_error = e
                    logger.warning(
                        "VLM attempt %d/%d for page %d failed after %.2fs: %s",
                        attempt+1, self.max_retries, page_index, elapsed, str(e)[:200],
                    )
                    if ai_req_logger:
                        ai_req_logger.error(
                            "vlm_extract_err | model=%s | page=%d | attempt=%d/%d | error_type=%s | error=%s",
                            self.vlm_model, page_index, attempt+1, self.max_retries,
                            type(e).__name__, str(e)[:300],
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

            raise RuntimeError(f"VLM page {page_index} failed after {self.max_retries} retries")

    async def _format_json_llm(
        self,
        raw_text: str,
        page_index: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
        survey_idx: int = 0,
        total_surveys: int = 1,
        total_pages: int = 1,
    ) -> dict:
        last_error = None
        system_prompt = build_text_format_prompt(page_index, raw_text)

        ctx = TraceContext(
            operation="format_json",
            model=self.text_model,
            page_idx=page_index,
            survey_idx=survey_idx,
            extra={"raw_text_len": len(raw_text)},
        ) if _HAS_TRACING else None

        async with (llm_trace(ctx) if ctx else nullcontext()):
            for attempt in range(self.max_retries):
                t0 = time.perf_counter()
                try:
                    if progress_callback:
                        progress_callback(ProcessingStatus(
                            survey_idx=survey_idx,
                            total_surveys=total_surveys,
                            page_idx=page_index,
                            total_pages=total_pages,
                            status="text_formatting" if attempt == 0 else "text_retrying",
                            message=f"Ankieta {survey_idx+1}, Strona {page_index+1}/{total_pages}: Text LLM formatowanie JSON..." if attempt == 0
                                    else f"Ankieta {survey_idx+1}, Strona {page_index+1}: Text LLM ponawianie ({attempt+1}/{self.max_retries})...",
                        ))

                    if ai_req_logger:
                        ai_req_logger.info(
                            "text_format | model=%s | page=%d | survey=%d | attempt=%d/%d | raw_text_len=%d",
                            self.text_model, page_index, survey_idx, attempt+1, self.max_retries, len(raw_text),
                        )
                    resp = await self._client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.text_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": "Przekształć tekst w JSON."},
                            ],
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
                    if ai_req_logger:
                        ai_req_logger.info(
                            "text_format_ok | model=%s | page=%d | keys=%s | latency=%.2fs",
                            self.text_model, page_index, list(parsed.keys()), elapsed,
                        )
                    logger.info("Text LLM page %d formatted in %.2fs", page_index, elapsed)
                    return parsed

                except json.JSONDecodeError as jde:
                    elapsed = time.perf_counter() - t0
                    last_error = jde
                    logger.error(
                        "JSONDecodeError page=%d attempt=%d/%d after %.2fs: %s | "
                        "Raw content (first 500 chars): %s",
                        page_index, attempt+1, self.max_retries, elapsed,
                        str(jde), content[:500],
                    )
                    if ai_req_logger:
                        ai_req_logger.error(
                            "text_format_json_err | model=%s | page=%d | attempt=%d/%d | json_error=%s | raw_preview=%s",
                            self.text_model, page_index, attempt+1, self.max_retries,
                            str(jde), content[:500],
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

                except Exception as e:
                    elapsed = time.perf_counter() - t0
                    last_error = e
                    logger.warning(
                        "Text LLM attempt %d/%d for page %d failed after %.2fs: %s",
                        attempt+1, self.max_retries, page_index, elapsed, str(e)[:200],
                    )
                    if ai_req_logger:
                        ai_req_logger.error(
                            "text_format_err | model=%s | page=%d | attempt=%d/%d | error_type=%s | error=%s",
                            self.text_model, page_index, attempt+1, self.max_retries,
                            type(e).__name__, str(e)[:300],
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

            raise RuntimeError(f"Text LLM page {page_index} failed after {self.max_retries} retries")

    async def _run_producer_consumer(
        self,
        survey_files: list[Path],
        survey_idx: int,
        total_surveys: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
    ) -> list[dict]:
        queue: asyncio.Queue[tuple[int, str] | None] = asyncio.Queue(maxsize=1)
        results: list[dict | None] = [None] * len(survey_files)
        total_pages = len(survey_files)

        async def producer():
            for page_idx, file_path in enumerate(survey_files):
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=page_idx, total_pages=total_pages,
                        status="vlm_extracting",
                        message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}/{total_pages}: VLM ekstrakcja tekstu...",
                    ))
                raw_text = await self._extract_text_vlm(
                    file_path, page_idx, progress_callback, survey_idx, total_surveys, total_pages
                )
                await queue.put((page_idx, raw_text))
            await queue.put(None)

        async def consumer():
            while True:
                item = await queue.get()
                if item is None:
                    break
                page_idx, raw_text = item
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=page_idx, total_pages=total_pages,
                        status="text_formatting",
                        message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}/{total_pages}: Text LLM formatowanie JSON...",
                    ))
                try:
                    result = await self._format_json_llm(
                        raw_text, page_idx, progress_callback, survey_idx, total_surveys, total_pages
                    )
                    results[page_idx] = result
                except json.JSONDecodeError as jde:
                    logger.error("Text LLM page %d JSONDecodeError: %s | raw: %s",
                                 page_idx, str(jde), raw_text[:1000])
                    if ai_req_logger:
                        ai_req_logger.error(
                            "text_format_json_err | model=%s | page=%d | json_error=%s | raw_preview=%s",
                            self.text_model, page_idx, str(jde), raw_text[:500],
                        )
                    if progress_callback:
                        progress_callback(ProcessingStatus(
                            survey_idx=survey_idx, total_surveys=total_surveys,
                            page_idx=page_idx, total_pages=total_pages,
                            status="page_error",
                            message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: Text LLM błąd — pominięto",
                        ))
                    results[page_idx] = {}
                except Exception as e:
                    logger.error("Text LLM page %d failed: %s", page_idx, e)
                    if ai_req_logger:
                        ai_req_logger.error(
                            "text_format_err | model=%s | page=%d | error_type=%s | error=%s",
                            self.text_model, page_idx, type(e).__name__, str(e)[:300],
                        )
                    if progress_callback:
                        progress_callback(ProcessingStatus(
                            survey_idx=survey_idx, total_surveys=total_surveys,
                            page_idx=page_idx, total_pages=total_pages,
                            status="page_error",
                            message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: Text LLM błąd — pominięto",
                        ))
                    results[page_idx] = {}
                queue.task_done()

        try:
            await asyncio.gather(producer(), consumer())
        except Exception as e:
            error_str = str(e).lower()
            if any(kw in error_str for kw in ("out of memory", "cuda", "oom", "insufficient memory")):
                logger.warning("VRAM OOM detected, falling back to sequential: %s", e)
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=0, total_pages=total_pages,
                        status="fallback_activated",
                        message="Za mało VRAM — przełączam na tryb sekwencyjny...",
                    ))
                return await self._run_sequential_fallback(survey_files, survey_idx, total_surveys, progress_callback)
            raise

        return [r if r is not None else {} for r in results]

    async def _run_sequential_fallback(
        self,
        survey_files: list[Path],
        survey_idx: int,
        total_surveys: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
    ) -> list[dict]:
        total_pages = len(survey_files)
        raw_texts: list[str] = []
        for page_idx, file_path in enumerate(survey_files):
            if progress_callback:
                progress_callback(ProcessingStatus(
                    survey_idx=survey_idx, total_surveys=total_surveys,
                    page_idx=page_idx, total_pages=total_pages,
                    status="vlm_extracting",
                    message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}/{total_pages}: VLM ekstrakcja tekstu (sekwencyjnie)...",
                ))
            raw_text = await self._extract_text_vlm(
                file_path, page_idx, progress_callback, survey_idx, total_surveys, total_pages
            )
            raw_texts.append(raw_text)

        page_results: list[dict] = []
        for page_idx, raw_text in enumerate(raw_texts):
            if progress_callback:
                progress_callback(ProcessingStatus(
                    survey_idx=survey_idx, total_surveys=total_surveys,
                    page_idx=page_idx, total_pages=total_pages,
                    status="text_formatting",
                    message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}/{total_pages}: Text LLM formatowanie JSON (sekwencyjnie)...",
                ))
            try:
                result = await self._format_json_llm(
                    raw_text, page_idx, progress_callback, survey_idx, total_surveys, total_pages
                )
                page_results.append(result)
            except Exception as e:
                logger.error("Sequential fallback page %d failed: %s", page_idx, e)
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=page_idx, total_pages=total_pages,
                        status="page_error",
                        message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: Text LLM błąd — pominięto",
                    ))
                page_results.append({})

        return page_results

    async def analyze_survey(
        self,
        survey_files: list[Path],
        survey_idx: int,
        total_surveys: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
    ) -> dict:
        """Zwraca słownik ze scalonymi danymi ankiety."""
        total_pages = len(survey_files)

        if progress_callback:
            progress_callback(ProcessingStatus(
                survey_idx=survey_idx, total_surveys=total_surveys,
                page_idx=0, total_pages=total_pages,
                status="survey_start",
                message=f"Ankieta {survey_idx+1}/{total_surveys}: rozpoczęcie przetwarzania ({total_pages} stron)...",
            ))

        t0 = time.perf_counter()

        page_results = await self._run_producer_consumer(
            survey_files, survey_idx, total_surveys, progress_callback
        )

        elapsed_total = time.perf_counter() - t0

        if progress_callback:
            progress_callback(ProcessingStatus(
                survey_idx=survey_idx, total_surveys=total_surveys,
                page_idx=total_pages, total_pages=total_pages,
                status="survey_done",
                message=f"Ankieta {survey_idx+1}/{total_surveys}: przetworzona",
                extra={"elapsed_s": f"{elapsed_total:.1f}", "pages": total_pages},
            ))

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

        try:
            validated = MedicalSurvey.from_ai_json(merged)
        except Exception as e:
            logger.error("Validation failed for survey %d: %s", survey_idx, e)
            raise

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