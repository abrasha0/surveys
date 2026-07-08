from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

CSV_HEADER = ["wiek", "plec", "skala_bólu", "uczelnia", "pola_wyboru", "needs_review"]


class MedicalSurvey(BaseModel):
    wiek: int = Field(ge=0, le=120)
    plec: Literal["M", "K"]
    skala_bólu: int = Field(ge=1, le=5)
    uczelnia: str
    pola_wyboru: dict[str, bool]
    needs_review: dict[str, bool]

    def to_csv_row(self) -> list:
        return [
            self.wiek,
            self.plec,
            self.skala_bólu,
            self.uczelnia,
            str(self.pola_wyboru),
            str(self.needs_review),
        ]

    @classmethod
    def from_ai_json(cls, data: dict) -> "MedicalSurvey":
        return cls(
            wiek=data.get("wiek"),
            plec=data.get("plec"),
            skala_bólu=data.get("skala_bólu"),
            uczelnia=data.get("uczelnia", ""),
            pola_wyboru=data.get("pola_wyboru", {}),
            needs_review=data.get("needs_review", {}),
        )


class SurveyResult(BaseModel):
    raw_response: str
    validated_data: MedicalSurvey
    confidence: float


class SurveyGroup(BaseModel):
    id: int
    files: list[Path]
    result: Optional[SurveyResult] = None
