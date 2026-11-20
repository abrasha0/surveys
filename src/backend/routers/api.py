import logging
import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ValidationError

from auth import get_current_user
from config import config
from data_handler import (
    archive_session,
    drafts_dir,
    export_csv_path,
    load_processed_data,
)
from domain.csv_export import rebuild_csv_from_processed
from domain.field_specs import ALL_FIELDS, FIELD_SPEC_BY_NAME
from domain.schemas import MedicalSurvey
from ingestion.file_grouping import scan_survey_directory
from worker import get_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


class SaveRequest(BaseModel):
    values: dict
    force: Optional[bool] = False


@router.get("/field-specs")
def get_field_specs():
    return [
        {
            "name": f.name,
            "label": f.label,
            "page": f.page,
            "kind": f.kind,
            "choices": f.choices,
            "min": f.min,
            "max": f.max,
            "csv_header": f.get_csv_header(),
            "conditional": f.conditional,
        }
        for f in ALL_FIELDS
    ]


@router.get("/surveys")
def list_surveys() -> list[dict]:
    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    worker = get_worker()
    worker.state.ensure_from_cache(groups)

    result = []
    for idx, group in enumerate(groups):
        survey_state = worker.state.get_survey_state(idx)
        status = survey_state.status if survey_state else "queued"
        result.append({
            "id": idx,
            "files": [p.name for p in group],
            "status": status,
            "can_edit": status in ("ready", "queued"),
        })
    return result


@router.get("/surveys/export/csv")
def export_csv():
    csv_path = export_csv_path()
    processed = load_processed_data()
    written = rebuild_csv_from_processed(processed, csv_path)
    if written == 0:
        raise HTTPException(status_code=404, detail="No verified surveys to export")
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="ankiety_wyniki.csv",
        headers={"Content-Type": "text/csv; charset=utf-8"}
    )


@router.get("/surveys/{survey_id}/pages/{page_num}/image")
def get_survey_image(survey_id: int, page_num: int, if_none_match: Optional[str] = None):
    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    if survey_id < 0 or survey_id >= len(groups):
        return Response(status_code=404, headers={"Cache-Control": "no-store, private"})

    group = groups[survey_id]
    if page_num < 0 or page_num >= len(group):
        return Response(
            status_code=410,
            headers={"Cache-Control": "no-store, private"},
        )

    file_path = group[page_num]
    if not file_path.is_file():
        return Response(status_code=404, headers={"Cache-Control": "no-store, private"})

    stat = file_path.stat()
    etag = hashlib.md5(f"{file_path.name}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()

    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={
            "ETag": f'"{etag}"',
            "Cache-Control": "no-store, private",
        })

    return FileResponse(
        path=str(file_path),
        headers={
            "Cache-Control": "no-store, private",
            "ETag": f'"{etag}"',
        },
    )


@router.get("/surveys/{survey_id}/result")
def get_survey_result(survey_id: int):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status not in ("ready", "verified", "error"):
        raise HTTPException(status_code=400, detail="Survey not yet processed")
    return {
        "id": survey_id,
        "status": survey.status,
        "result": survey.result,
        "draft": survey.draft_values,
        "error": survey.error_message,
    }


class StartRequest(BaseModel):
    batch_size: int = 0


@router.post("/processing/start")
async def processing_start(request: StartRequest):
    worker = get_worker()
    if worker.state.is_running:
        raise HTTPException(status_code=400, detail="Processing already in progress")

    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    if not groups:
        raise HTTPException(status_code=404, detail="No surveys found")

    batch_size = request.batch_size
    if batch_size < 0:
        raise HTTPException(status_code=400, detail="batch_size must be >= 0")

    await worker.start(groups, batch_size=batch_size)
    effective = batch_size if batch_size > 0 else len(groups)
    return {"status": "started", "total": len(groups), "batch_size": effective}


@router.get("/processing/status")
async def processing_status():
    worker = get_worker()
    return worker.state.to_global_dict()


@router.post("/processing/stop")
async def processing_stop():
    worker = get_worker()
    if not worker.state.is_running:
        raise HTTPException(status_code=400, detail="Worker not running")
    await worker.stop()
    return {"status": "stopping"}


@router.post("/session/clear")
def clear_session():
    worker = get_worker()
    if worker.state.is_running:
        raise HTTPException(status_code=400, detail="Cannot clear session while processing")

    archive_dir = archive_session()

    draft_dir = drafts_dir()
    if draft_dir.exists():
        shutil.rmtree(draft_dir)

    worker.state.reset()

    logger.info("Session cleared")
    return {"status": "cleared", "archive": archive_dir.name if archive_dir else None}


@router.post("/surveys/{survey_id}/unverify")
def unverify_survey(survey_id: int):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status != "verified":
        raise HTTPException(status_code=400, detail=f"Survey not in 'verified' status (current: {survey.status})")
    worker.state.unverify(survey_id)
    return {"status": "unverified", "survey_id": survey_id}


class DraftRequest(BaseModel):
    values: dict


@router.post("/surveys/{survey_id}/draft")
def save_draft(survey_id: int, request: DraftRequest):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    draft_dir = drafts_dir()
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / f"survey_{survey_id}.json"
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(request.values, f, ensure_ascii=False, indent=2)
    survey.draft_values = request.values
    return {"status": "saved"}


@router.post("/session/finalize")
def finalize_session():
    worker = get_worker()
    if worker.state.is_running:
        raise HTTPException(status_code=400, detail="Cannot finalize while worker is running")

    verified = [s for s in worker.state.surveys if s.status == "verified"]
    if not verified:
        raise HTTPException(status_code=400, detail="No verified surveys to finalize")

    # Rebuild the whole file, like the CSV export, so re-verified surveys are not appended twice.
    csv_path = export_csv_path()
    written = rebuild_csv_from_processed(load_processed_data(), csv_path)
    for survey in verified:
        worker.state.mark_csv_written(survey.id)

    total_errors = sum(1 for s in worker.state.surveys if s.status == "error")
    return {
        "status": "finalized",
        "csv_path": csv_path,
        "total_verified": len(verified),
        "written": written,
        "total_errors": total_errors,
    }


@router.post("/surveys/{survey_id}/save")
def save_survey(survey_id: int, request: SaveRequest):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    if survey.status not in ("ready", "error"):
        raise HTTPException(
            status_code=400,
            detail=f"Survey not in 'ready' or 'error' status (current: {survey.status})",
        )

    normalized = {}
    validation_errors = {}
    for f in ALL_FIELDS:
        raw = request.values.get(f.name)
        if isinstance(raw, str) and not raw.strip():
            raw = None  # A cleared field means "no answer", not an invalid value.
        spec = FIELD_SPEC_BY_NAME.get(f.name)
        if spec and spec.kind == "radio":
            if raw is not None and spec.choices and raw in spec.choices:
                normalized[f.name] = raw
            elif raw is not None and spec.choices:
                matched = False
                for choice in spec.choices:
                    if raw.lower().strip() == choice.lower().strip():
                        normalized[f.name] = choice
                        matched = True
                        break
                if not matched:
                    normalized[f.name] = None
                    validation_errors[f.name] = f"Invalid choice: '{raw}'"
            else:
                normalized[f.name] = None
        elif spec and spec.kind == "number":
            try:
                value = int(raw) if raw is not None else None
            except (ValueError, TypeError):
                normalized[f.name] = None
                validation_errors[f.name] = f"Invalid number: '{raw}'"
            else:
                normalized[f.name] = value
                too_low = value is not None and spec.min is not None and value < spec.min
                too_high = value is not None and spec.max is not None and value > spec.max
                if too_low or too_high:
                    validation_errors[f.name] = f"Value {value} outside range {spec.min}-{spec.max}"
        elif spec and spec.kind == "text":
            normalized[f.name] = str(raw).strip() if raw is not None else ""
        else:
            normalized[f.name] = raw
    try:
        MedicalSurvey(**normalized)
    except ValidationError as e:
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"]) if error["loc"] else "unknown"
            validation_errors[field] = error["msg"]

    if validation_errors and not request.force:
        raise HTTPException(status_code=422, detail={
            "message": "Validation errors",
            "errors": validation_errors,
        })

    worker.state.mark_verified(survey_id, result=normalized)

    logger.info("Survey %d approved (CSV pending finalization)", survey_id)
    return {
        "status": "saved",
        "survey_id": survey_id,
    }
