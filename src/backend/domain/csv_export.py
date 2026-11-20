import csv
import logging
from pathlib import Path

from domain.schemas import MedicalSurvey
from domain.field_specs import CSV_FIELDS

logger = logging.getLogger(__name__)

# CSV header built from field_specs
CSV_HEADER = ["Sygnatura czasowa"] + [f.get_csv_header() for f in CSV_FIELDS]


def rebuild_csv_from_processed(processed_data: dict, csv_path: str) -> int:
    """Rewrite the results CSV from processed.json, using only verified surveys."""
    filepath = Path(csv_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    surveys = processed_data.get("surveys", {}) if isinstance(processed_data, dict) else {}

    def _sort_key(item):
        key = item[0]
        try:
            return int(key)
        except (TypeError, ValueError):
            return key

    rows = []
    for key, entry in sorted(surveys.items(), key=_sort_key):
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "verified":
            continue
        result = entry.get("result")
        if not isinstance(result, dict) or not result:
            continue
        try:
            survey = MedicalSurvey(**result)
        except Exception as e:
            logger.warning("Skipped survey %s while rebuilding CSV: %s", key, e)
            continue
        rows.append(survey.to_csv_row())

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(row)

    logger.info("Rebuilt CSV %s: %d verified rows", csv_path, len(rows))
    return len(rows)
