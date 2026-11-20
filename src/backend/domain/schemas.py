import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from domain.field_specs import FIELD_SPEC_BY_NAME, ALL_FIELDS, CSV_FIELDS

from dataclasses import dataclass
from pathlib import Path

@dataclass
class SurveyGroup:
    id: int
    files: list[Path]

class MedicalSurvey(BaseModel):
    # A. Demografia
    p1_plec: Optional[str] = None
    p2_wiek: Optional[int] = None
    p3_miejsce: Optional[str] = None
    p4_stan: Optional[str] = None
    p5_forma: Optional[str] = None
    p5_inne: str = ""
    p6_stopien: Optional[str] = None
    p7_uczelnia: str = ""

    # B. Aktywność zawodowa
    p8_praca: Optional[str] = None
    p9_system: Optional[str] = None
    p9_inne: str = ""
    p10_oddzial: Optional[str] = None
    p10_inne: str = ""
    p11_staz: str = ""

    # C. Styl życia
    p12_sen: Optional[str] = None
    p13_ekran: Optional[str] = None
    p14_kofeina: Optional[str] = None

    # D. MFIS (21)
    mfis_1: Optional[str] = None
    mfis_2: Optional[str] = None
    mfis_3: Optional[str] = None
    mfis_4: Optional[str] = None
    mfis_5: Optional[str] = None
    mfis_6: Optional[str] = None
    mfis_7: Optional[str] = None
    mfis_8: Optional[str] = None
    mfis_9: Optional[str] = None
    mfis_10: Optional[str] = None
    mfis_11: Optional[str] = None
    mfis_12: Optional[str] = None
    mfis_13: Optional[str] = None
    mfis_14: Optional[str] = None
    mfis_15: Optional[str] = None
    mfis_16: Optional[str] = None
    mfis_17: Optional[str] = None
    mfis_18: Optional[str] = None
    mfis_19: Optional[str] = None
    mfis_20: Optional[str] = None
    mfis_21: Optional[str] = None

    # E. Stan zdrowia
    choroba_anemia: Optional[str] = None
    choroba_tarczyca: Optional[str] = None
    tarczyca_jakie: str = ""
    choroba_inne: str = ""

    # F. Jakość snu
    sen_1: Optional[str] = None
    sen_2: Optional[str] = None
    sen_3: Optional[str] = None
    sen_4: Optional[str] = None
    sen_5: Optional[str] = None
    sen_6: Optional[str] = None
    sen_7: Optional[str] = None
    sen_8: Optional[str] = None

    # G. CES-D (20)
    depr_1: Optional[str] = None
    depr_2: Optional[str] = None
    depr_3: Optional[str] = None
    depr_4: Optional[str] = None
    depr_5: Optional[str] = None
    depr_6: Optional[str] = None
    depr_7: Optional[str] = None
    depr_8: Optional[str] = None
    depr_9: Optional[str] = None
    depr_10: Optional[str] = None
    depr_11: Optional[str] = None
    depr_12: Optional[str] = None
    depr_13: Optional[str] = None
    depr_14: Optional[str] = None
    depr_15: Optional[str] = None
    depr_16: Optional[str] = None
    depr_17: Optional[str] = None
    depr_18: Optional[str] = None
    depr_19: Optional[str] = None
    depr_20: Optional[str] = None

    # --- Walidacja i normalizacja ---
    @field_validator("*", mode="before")
    @classmethod
    def normalize_field(cls, v, info):
        field_name = info.field_name
        spec = FIELD_SPEC_BY_NAME.get(field_name)
        if not spec:
            return v
        # Jeśli to select, sprawdź czy wartość jest w dozwolonych
        if spec.kind == "radio":
            if v is None:
                return None
            if isinstance(v, str):
                # Dopasowanie przybliżone – można rozszerzyć
                if v in spec.choices:
                    return v
                # Próba przybliżonego dopasowania (np. małe litery)
                for choice in spec.choices:
                    if v.lower().strip() == choice.lower().strip():
                        return choice
                return None
            return None
        # Dla liczby
        if spec.kind == "number":
            if v is None:
                return None
            try:
                return int(v)
            except (ValueError, TypeError):
                return None
        # Dla tekstu
        if spec.kind == "text":
            if v is None:
                return ""
            return str(v).strip()
        return v

    def to_csv_row(self) -> list:
        dt = datetime.now()
        ts = f"{dt.month}/{dt.day}/{dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
        row = [ts]
        for f in CSV_FIELDS:
            val = getattr(self, f.name, "")
            cell = str(val) if val is not None else ""
            cell = cell.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
            row.append(cell)
        return row

    @classmethod
    def from_ai_json(cls, data: dict) -> "MedicalSurvey":
        kwargs = {}
        for f in ALL_FIELDS:
            raw = data.get(f.name)
            if f.kind == "number":
                raw = _parse_number_in_range(raw, f.min, f.max)
            kwargs[f.name] = raw
        return cls(**kwargs)


def _parse_number_in_range(raw, min_value: int | None, max_value: int | None) -> int | None:
    """Read a number from OCR output; drop it when it falls outside the allowed range.

    The reviewer fills in a dropped value by hand, so one misread number does not
    fail the whole survey.
    """
    if isinstance(raw, str):
        m = re.search(r"\d+", raw)
        raw = m.group() if m else None
    try:
        value = int(raw) if raw is not None else None
    except (ValueError, TypeError):
        return None
    if value is None:
        return None
    if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
        return None
    return value
