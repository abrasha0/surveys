import csv
import logging
from pathlib import Path

from domain.schemas import MedicalSurvey
from domain.field_specs import CSV_FIELDS

logger = logging.getLogger(__name__)

# Nagłówek CSV na podstawie field_specs
CSV_HEADER = ["Sygnatura czasowa"] + [f.get_csv_header() for f in CSV_FIELDS]


def save_survey_to_csv(data: MedicalSurvey, csv_path: str):
    filepath = Path(csv_path)
    exists = filepath.exists()
    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        if not exists:
            writer.writerow(CSV_HEADER)
            logger.info("Utworzono plik CSV: %s", csv_path)
        writer.writerow(data.to_csv_row())
    logger.debug("Dodano wiersz do CSV: %s", csv_path)


def rebuild_csv_from_processed(processed_data: dict, csv_path: str) -> int:
    """Odbudowuje wyniki.csv w całości z processed.json (ankiety ze statusem 'verified')."""
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
            logger.warning("Pominięto ankietę %s podczas odbudowy CSV: %s", key, e)
            continue
        rows.append(survey.to_csv_row())

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(row)

    logger.info("Odbudowano CSV %s: %d zweryfikowanych wierszy", csv_path, len(rows))
    return len(rows)
