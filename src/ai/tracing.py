import time
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_client = None
_client_attempted = False


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

    from config import config
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
async def vlm_trace(ctx: TraceContext):
    client = _get_client()
    if client is None:
        yield None
        return

    from config import config
    tags = ["vlm"]
    if ctx.model:
        tags.append(ctx.model)
    if ctx.page_idx >= 0:
        tags.append(f"page_{ctx.page_idx}")
    if ctx.survey_idx >= 0:
        tags.append(f"survey_{ctx.survey_idx}")

    run = client.create_run(
        name=f"vlm_{ctx.operation}",
        project_name=config.langsmith["project"],
        run_type="chain",
        tags=tags,
        extra={
            "model": ctx.model,
            "page_idx": ctx.page_idx,
            "survey_idx": ctx.survey_idx,
            **ctx.extra,
        },
    )

    t0 = time.perf_counter()
    error = None
    result = None
    try:
        result = yield run
    except Exception as e:
        error = e
        raise
    finally:
        elapsed = time.perf_counter() - t0
        try:
            client.update_run(
                run.id,
                end_time=time.time(),
                extra={
                    "latency_s": round(elapsed, 3),
                    "error": str(error)[:500] if error else None,
                },
            )
            if error:
                client.update_run(run.id, error=str(error)[:500])
        except Exception as e:
            logger.warning("LangSmith vlm_trace update_run failed: %s", e)


@asynccontextmanager
async def llm_trace(ctx: TraceContext):
    client = _get_client()
    if client is None:
        yield None
        return

    from config import config
    tags = ["text_llm"]
    if ctx.model:
        tags.append(ctx.model)
    if ctx.page_idx >= 0:
        tags.append(f"page_{ctx.page_idx}")
    if ctx.survey_idx >= 0:
        tags.append(f"survey_{ctx.survey_idx}")

    run = client.create_run(
        name=f"llm_{ctx.operation}",
        project_name=config.langsmith["project"],
        run_type="chain",
        tags=tags,
        extra={
            "model": ctx.model,
            "page_idx": ctx.page_idx,
            "survey_idx": ctx.survey_idx,
            **ctx.extra,
        },
    )

    t0 = time.perf_counter()
    error = None
    result = None
    try:
        result = yield run
    except Exception as e:
        error = e
        raise
    finally:
        elapsed = time.perf_counter() - t0
        try:
            client.update_run(
                run.id,
                end_time=time.time(),
                extra={
                    "latency_s": round(elapsed, 3),
                    "error": str(error)[:500] if error else None,
                },
            )
            if error:
                client.update_run(run.id, error=str(error)[:500])
        except Exception as e:
            logger.warning("LangSmith llm_trace update_run failed: %s", e)


@asynccontextmanager
async def io_trace(op_name: str, metadata: dict | None = None):
    client = _get_client()
    if client is None:
        yield None
        return

    from config import config
    tags = ["io"]

    run = client.create_run(
        name=f"io_{op_name}",
        project_name=config.langsmith["project"],
        run_type="tool",
        tags=tags,
        extra=metadata or {},
    )

    t0 = time.perf_counter()
    error = None
    try:
        yield run
    except Exception as e:
        error = e
        raise
    finally:
        elapsed = time.perf_counter() - t0
        try:
            client.update_run(
                run.id,
                end_time=time.time(),
                extra={
                    "latency_s": round(elapsed, 3),
                    "error": str(error)[:500] if error else None,
                },
            )
            if error:
                client.update_run(run.id, error=str(error)[:500])
        except Exception as e:
            logger.warning("LangSmith io_trace update_run failed: %s", e)
