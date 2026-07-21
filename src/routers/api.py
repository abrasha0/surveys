import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from auth import get_current_user
from config import config
from data_handler import export_csv_path
from domain.csv_export import save_survey_to_csv
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

    result = []
    for idx, group in enumerate(groups):
        survey_state = worker.state.get_survey_state(idx)
        status = survey_state.status if survey_state else "queued"
        result.append({
            "id": idx,
            "files": [p.name for p in group],
            "status": status,
        })
    return result


@router.get("/surveys/{survey_id}/pages/{page_num}/image")
def get_survey_image(survey_id: int, page_num: int):
    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    if survey_id < 0 or survey_id >= len(groups):
        raise HTTPException(status_code=404, detail=f"Survey {survey_id} not found")

    group = groups[survey_id]
    if page_num < 0 or page_num >= len(group):
        raise HTTPException(
            status_code=400,
            detail=f"Page {page_num} out of range (0-{len(group) - 1})",
        )

    file_path = group[page_num]
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path.name}")

    return FileResponse(path=str(file_path), media_type="image/jpeg")


@router.get("/surveys/{survey_id}/result")
def get_survey_result(survey_id: int):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status not in ("ready", "error"):
        raise HTTPException(status_code=400, detail="Survey not yet processed")
    return {
        "id": survey_id,
        "status": survey.status,
        "result": survey.result,
        "error": survey.error_message,
    }


@router.post("/processing/start")
async def processing_start():
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

    await worker.start(groups)
    return {"status": "started", "total": len(groups)}


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


@router.post("/surveys/{survey_id}/save")
def save_survey(survey_id: int, request: SaveRequest):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    if survey.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Survey not in 'ready' status (current: {survey.status})",
        )

    normalized = {}
    validation_errors = {}
    for f in ALL_FIELDS:
        raw = request.values.get(f.name)
        spec = FIELD_SPEC_BY_NAME.get(f.name)
        if spec and spec.kind == "select":
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
                normalized[f.name] = int(raw) if raw is not None else None
            except (ValueError, TypeError):
                normalized[f.name] = None
                validation_errors[f.name] = f"Invalid number: '{raw}'"
        elif spec and spec.kind == "text":
            normalized[f.name] = str(raw).strip() if raw is not None else ""
        else:
            normalized[f.name] = raw
    try:
        survey_data = MedicalSurvey(**normalized)
    except ValidationError as e:
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"]) if error["loc"] else "unknown"
            validation_errors[field] = error["msg"]

    if validation_errors and not request.force:
        raise HTTPException(status_code=422, detail={
            "message": "Validation errors",
            "errors": validation_errors,
        })

    if validation_errors and request.force:
        survey_data = MedicalSurvey(**normalized)

    csv_path = export_csv_path()
    save_survey_to_csv(survey_data, csv_path)

    worker.state.mark_verified(survey_id)

    logger.info("Survey %d saved to CSV: %s", survey_id, csv_path)
    return {
        "status": "saved",
        "survey_id": survey_id,
        "csv_path": csv_path,
    }
