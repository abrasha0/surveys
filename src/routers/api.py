import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from auth import get_current_user
from config import config
from ingestion.file_grouping import scan_survey_directory
from worker import get_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


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
def save_survey(survey_id: int):
    raise HTTPException(status_code=501, detail="Not implemented yet — Etap 4")
