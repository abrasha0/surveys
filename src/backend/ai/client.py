import asyncio
import base64
import json
import logging
import time
from contextlib import nullcontext
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import httpx
from PIL import Image

from config import config
from domain.schemas import MedicalSurvey
from ai.prompts import build_vlm_prompt, build_text_format_prompt
from domain.field_specs import PAGE_MAP
import logger as _logger_mod

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
_SHORTEN_IO = config.logging["shorten_models_io"]
_MAX_IO_SIZE = config.logging["max_models_io_size"]


def _truncate(text: str, limit: int | None = None) -> str:
    if not _SHORTEN_IO:
        return text
    return text[: limit or _MAX_IO_SIZE]


@dataclass
class ProcessingStatus:
    survey_idx: int
    total_surveys: int
    page_idx: int
    total_pages: int
    status: str          # "survey_start", "vlm_extracting", "vlm_retrying", "vlm_reocr", "text_formatting", "text_retrying",
                         # "page_error", "survey_done", "batch_done", "survey_error"
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

        buf = BytesIO()
        img.save(buf, format="PNG")
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

                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.info(
                            "vlm_extract | model=%s | page=%d | survey=%d | attempt=%d/%d | file=%s | prompt=%s",
                            self.vlm_model, page_index, survey_idx, attempt+1, self.max_retries,
                            image_path.name, _truncate(system_prompt),
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
                            "think": False,
                            "options": {
                                "num_ctx": _OLLAMA_NUM_CTX,
                                "temperature": _OLLAMA_TEMPERATURE,
                                "num_predict": config.ai["num_predict_vlm"],
                            },
                        },
                    )
                    elapsed = time.perf_counter() - t0
                    resp.raise_for_status()
                    body = resp.json()
                    raw_text = body.get("message", {}).get("content", "")
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.info(
                            "vlm_extract_ok | model=%s | page=%d | chars=%d | latency=%.2fs | output_preview=%s",
                            self.vlm_model, page_index, len(raw_text), elapsed,
                            _truncate(raw_text),
                        )
                    logger.info("VLM page %d extracted %d chars in %.2fs", page_index, len(raw_text), elapsed)
                    return raw_text

                except httpx.HTTPStatusError as hse:
                    elapsed = time.perf_counter() - t0
                    last_error = hse
                    logger.warning(
                        "VLM HTTP %d page %d attempt %d/%d after %.2fs: %s",
                        hse.response.status_code, page_index, attempt+1, self.max_retries, elapsed,
                        _truncate(hse.response.text),
                    )
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.error(
                            "vlm_extract_err | model=%s | page=%d | attempt=%d/%d | error_type=HTTPStatusError | http_status=%d | error=%s",
                            self.vlm_model, page_index, attempt+1, self.max_retries,
                            hse.response.status_code, _truncate(hse.response.text),
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

                except Exception as e:
                    elapsed = time.perf_counter() - t0
                    last_error = e
                    logger.warning(
                        "VLM attempt %d/%d for page %d failed after %.2fs: %s",
                        attempt+1, self.max_retries, page_index, elapsed, _truncate(str(e)),
                    )
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.error(
                            "vlm_extract_err | model=%s | page=%d | attempt=%d/%d | error_type=%s | error=%s",
                            self.vlm_model, page_index, attempt+1, self.max_retries,
                            type(e).__name__, _truncate(str(e)),
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

            raise RuntimeError(
                f"VLM page {page_index} failed after {self.max_retries} retries"
            ) from last_error

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
                content = ""
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

                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.info(
                            "text_format | model=%s | page=%d | survey=%d | attempt=%d/%d | prompt=%s | raw_text_len=%d",
                            self.text_model, page_index, survey_idx, attempt+1, self.max_retries,
                            _truncate(system_prompt), len(raw_text),
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
                                "num_predict": config.ai["num_predict_text"],
                            },
                        },
                    )
                    elapsed = time.perf_counter() - t0
                    resp.raise_for_status()
                    content = resp.text
                    body = resp.json()
                    content = body.get("message", {}).get("content", "")
                    parsed = json.loads(content)
                    if not isinstance(parsed, dict):
                        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.info(
                            "text_format_ok | model=%s | page=%d | keys=%s | latency=%.2fs | output_preview=%s",
                            self.text_model, page_index, list(parsed.keys()), elapsed,
                            _truncate(json.dumps(parsed, ensure_ascii=False)),
                        )
                    logger.info("Text LLM page %d formatted in %.2fs", page_index, elapsed)
                    return parsed

                except json.JSONDecodeError as jde:
                    elapsed = time.perf_counter() - t0
                    last_error = jde
                    logger.error(
                        "JSONDecodeError page=%d attempt=%d/%d after %.2fs: %s | "
                        "Raw content: %s",
                        page_index, attempt+1, self.max_retries, elapsed,
                        str(jde), _truncate(content),
                    )
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.error(
                            "text_format_json_err | model=%s | page=%d | attempt=%d/%d | json_error=%s | raw_preview=%s",
                            self.text_model, page_index, attempt+1, self.max_retries,
                            str(jde), _truncate(content),
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

                except Exception as e:
                    elapsed = time.perf_counter() - t0
                    last_error = e
                    logger.warning(
                        "Text LLM attempt %d/%d for page %d failed after %.2fs: %s",
                        attempt+1, self.max_retries, page_index, elapsed, _truncate(str(e)),
                    )
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.error(
                            "text_format_err | model=%s | page=%d | attempt=%d/%d | error_type=%s | error=%s",
                            self.text_model, page_index, attempt+1, self.max_retries,
                            type(e).__name__, _truncate(str(e)),
                        )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

            raise RuntimeError(
                f"Text LLM page {page_index} failed after {self.max_retries} retries"
            ) from last_error

    async def _process_pages_sequential(
        self,
        survey_files: list[Path],
        survey_idx: int,
        total_surveys: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
        page_done_callback: Callable[[int, int], None] | None = None,
    ) -> list[dict]:
        """Przetwarza strony sekwencyjnie: dla każdej strony VLM → Text LLM → result.
        page_done_callback(survey_id, page_idx) wywoływane przy przejściu do kolejnej strony."""
        total_pages = len(survey_files)
        page_results: list[dict] = []

        re_ocr_threshold = config.processing.get("re_ocr_threshold", 0.0)
        re_ocr_max_attempts = config.processing.get("re_ocr_max_attempts", 0)

        for page_idx, file_path in enumerate(survey_files):
            if page_idx > 0 and page_done_callback:
                page_done_callback(survey_idx, page_idx - 1)

            page_start = time.perf_counter()
            logger.info(
                "Processing page %d/%d for survey %d — step 1/2: VLM extraction",
                page_idx + 1, total_pages, survey_idx + 1,
            )
            try:
                raw_text = await self._extract_text_vlm(
                    file_path, page_idx, progress_callback, survey_idx, total_surveys, total_pages
                )
            except Exception as e:
                page_elapsed = time.perf_counter() - page_start
                logger.error("VLM failed for page %d of survey %d: %s", page_idx + 1, survey_idx + 1, e)
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=page_idx, total_pages=total_pages,
                        status="page_error",
                        message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: VLM błąd — pominięto",
                        extra={"elapsed_s": f"{page_elapsed:.1f}"},
                    ))
                page_results.append({})
                continue

            stripped_text = raw_text.strip()
            if stripped_text == "" or stripped_text == "[PUSTA_STRONA]" or len(stripped_text) < 10:
                page_elapsed = time.perf_counter() - page_start
                logger.info(
                    "Empty VLM output for page %d of survey %d — skipping text formatting (length=%d)",
                    page_idx + 1, survey_idx + 1, len(stripped_text),
                )
                if progress_callback:
                    progress_callback(ProcessingStatus(
                        survey_idx=survey_idx, total_surveys=total_surveys,
                        page_idx=page_idx, total_pages=total_pages,
                        status="page_done",
                        message="",
                        extra={"elapsed_s": f"{page_elapsed:.1f}", "empty_page": True},
                    ))
                page_results.append({})
                continue

            logger.info(
                "Processing page %d/%d for survey %d — step 2/2: Text LLM formatting (raw_text=%d chars)",
                page_idx + 1, total_pages, survey_idx + 1, len(raw_text),
            )

            page_fields = PAGE_MAP.get(page_idx, [])
            page_field_names = {f.name for f in page_fields}

            re_ocr_attempt = 0
            while True:
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
                    page_elapsed = time.perf_counter() - page_start

                    if re_ocr_threshold > 0.0 and re_ocr_attempt < re_ocr_max_attempts:
                        fill_ratio = self._compute_page_fill_ratio(result, page_field_names)
                        if fill_ratio < re_ocr_threshold:
                            re_ocr_attempt += 1
                            logger.info(
                                "Page %d fill ratio %.0f%% below threshold %.0f%% — re-OCR attempt %d/%d",
                                page_idx, fill_ratio * 100, re_ocr_threshold * 100,
                                re_ocr_attempt, re_ocr_max_attempts,
                            )
                            if progress_callback:
                                progress_callback(ProcessingStatus(
                                    survey_idx=survey_idx, total_surveys=total_surveys,
                                    page_idx=page_idx, total_pages=total_pages,
                                    status="vlm_reocr",
                                    message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: ponowna analiza VLM ({re_ocr_attempt}/{re_ocr_max_attempts})",
                                ))
                            raw_text = await self._extract_text_vlm(
                                file_path, page_idx, progress_callback, survey_idx, total_surveys, total_pages
                            )
                            stripped_text = raw_text.strip()
                            if stripped_text == "" or stripped_text == "[PUSTA_STRONA]" or len(stripped_text) < 10:
                                logger.info(
                                    "Empty VLM output on re-OCR for page %d of survey %d — skipping (length=%d)",
                                    page_idx + 1, survey_idx + 1, len(stripped_text),
                                )
                                page_results.append({})
                                break
                            continue

                    if progress_callback:
                        progress_callback(ProcessingStatus(
                            survey_idx=survey_idx, total_surveys=total_surveys,
                            page_idx=page_idx, total_pages=total_pages,
                            status="page_done",
                            message="",
                            extra={"elapsed_s": f"{page_elapsed:.1f}"},
                        ))
                    page_results.append(result)
                    break
                except Exception as e:
                    page_elapsed = time.perf_counter() - page_start
                    logger.error("Text LLM failed for page %d of survey %d: %s", page_idx + 1, survey_idx + 1, e)
                    if _logger_mod.ai_req_logger:
                        _logger_mod.ai_req_logger.error(
                            "text_format_err | model=%s | page=%d | survey=%d | error_type=%s | error=%s",
                            self.text_model, page_idx, survey_idx, type(e).__name__, _truncate(str(e)),
                        )
                    if progress_callback:
                        progress_callback(ProcessingStatus(
                            survey_idx=survey_idx, total_surveys=total_surveys,
                            page_idx=page_idx, total_pages=total_pages,
                            status="page_error",
                            message=f"Ankieta {survey_idx+1}, Strona {page_idx+1}: Text LLM błąd — pominięto",
                            extra={"elapsed_s": f"{page_elapsed:.1f}"},
                        ))
                    page_results.append({})
                    break

        if page_done_callback:
            page_done_callback(survey_idx, total_pages - 1)

        return page_results

    def _compute_page_fill_ratio(self, page_result: dict, expected_fields: set[str]) -> float:
        if not expected_fields:
            return 1.0
        if not page_result:
            return 0.0
        filled = sum(
            1 for name in expected_fields
            if page_result.get(name) not in (None, "", [], {})
        )
        return filled / len(expected_fields)

    async def analyze_survey(
        self,
        survey_files: list[Path],
        survey_idx: int,
        total_surveys: int,
        progress_callback: Callable[[ProcessingStatus], None] | None = None,
        page_done_callback: Callable[[int, int], None] | None = None,
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

        page_results = await self._process_pages_sequential(
            survey_files, survey_idx, total_surveys, progress_callback, page_done_callback
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
        for part in page_results:
            if not part:
                continue
            for k, v in part.items():
                if v is not None:
                    merged.setdefault(k, v)

        try:
            validated = MedicalSurvey.from_ai_json(merged)
        except Exception as e:
            logger.error("Validation failed for survey %d: %s", survey_idx, e)
            raise

        result_dict = validated.model_dump()
        return result_dict
