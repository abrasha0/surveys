import csv
import logging
from pathlib import Path
from domain.schemas import MedicalSurvey
from domain.field_specs import ALL_FIELDS

logger = logging.getLogger(__name__)

# Nagłówek CSV na podstawie field_specs
CSV_HEADER = ["Sygnatura czasowa"] + [f.get_csv_header() for f in ALL_FIELDS]

def save_survey_to_csv(data: MedicalSurvey, csv_path: str):
    filepath = Path(csv_path)
    exists = filepath.exists()
    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(CSV_HEADER)
            logger.info("Utworzono plik CSV: %s", csv_path)
        writer.writerow(data.to_csv_row())
    logger.debug("Dodano wiersz do CSV: %s", csv_path)