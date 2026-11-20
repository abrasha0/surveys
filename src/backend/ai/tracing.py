import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from config import config

logger = logging.getLogger(__name__)

_SHORTEN_IO = config.logging["shorten_models_io"]
_MAX_IO_SIZE = config.logging["max_models_io_size"]

_client = None
_client_attempted = False


def _truncate(text: str, limit: int | None = None) -> str:
    if not _SHORTEN_IO:
        return text
    return text[: limit or _MAX_IO_SIZE]


@dataclass
class TraceContext:
    operation: str
    model: str = ""
    page_idx: int = -1
    survey_idx: int = -1
    extra: dict = field(default_factory=dict)


def _get_client():
    global _client, _client_attempted
    if _client_attempted:
        return _client
    _client_attempted = True

    if not config.langsmith["tracing_v2"] or not config.langsmith["endpoint"]:
        logger.debug("LangSmith tracing disabled")
        return None

    try:
        from langsmith import Client
        _client = Client(
            api_url=config.langsmith["endpoint"],
            api_key=config.langsmith["api_key"],
        )
        logger.info("LangSmith client initialized, project=%s", config.langsmith["project"])
    except ImportError:
        logger.warning("langsmith package not installed — tracing disabled")
    except Exception as e:
        logger.warning("LangSmith client init failed: %s", e)

    return _client


def get_langsmith_client():
    return _get_client()


@asynccontextmanager
async def _trace_run(name: str, run_type: str, tags: list[str], metadata: dict):
    """Record the wrapped block as one LangSmith run.

    Tracing failures are logged and never interrupt the traced operation.
    """
    client = _get_client()
    if client is None:
        yield None
        return

    run_id = uuid4()
    try:
        client.create_run(
            name=name,
            inputs={},
            run_type=run_type,
            id=run_id,
            project_name=config.langsmith["project"],
            start_time=datetime.now(timezone.utc),
            tags=tags,
            extra={"metadata": metadata},
        )
    except Exception as e:
        logger.warning("LangSmith create_run failed for %s: %s", name, e)
        yield None
        return

    t0 = time.perf_counter()
    error = None
    try:
        yield run_id
    except Exception as e:
        error = e
        raise
    finally:
        try:
            client.update_run(
                run_id,
                end_time=datetime.now(timezone.utc),
                outputs={"latency_s": round(time.perf_counter() - t0, 3)},
                error=_truncate(str(error)) if error else None,
            )
        except Exception as e:
            logger.warning("LangSmith update_run failed for %s: %s", name, e)


def _model_tags(kind: str, ctx: TraceContext) -> list[str]:
    tags = [kind]
    if ctx.model:
        tags.append(ctx.model)
    if ctx.page_idx >= 0:
        tags.append(f"page_{ctx.page_idx}")
    if ctx.survey_idx >= 0:
        tags.append(f"survey_{ctx.survey_idx}")
    return tags


def _model_metadata(ctx: TraceContext) -> dict:
    return {
        "model": ctx.model,
        "page_idx": ctx.page_idx,
        "survey_idx": ctx.survey_idx,
        **ctx.extra,
    }


def vlm_trace(ctx: TraceContext):
    return _trace_run(f"vlm_{ctx.operation}", "chain", _model_tags("vlm", ctx), _model_metadata(ctx))


def llm_trace(ctx: TraceContext):
    return _trace_run(f"llm_{ctx.operation}", "chain", _model_tags("text_llm", ctx), _model_metadata(ctx))


def io_trace(op_name: str, metadata: dict | None = None):
    return _trace_run(f"io_{op_name}", "tool", ["io"], metadata or {})
