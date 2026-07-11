from datetime import datetime
from typing import Optional, Literal, get_args
from pydantic import BaseModel, Field, field_validator
from domain.field_specs import FIELD_SPEC_BY_NAME, ALL_FIELDS

from dataclasses import dataclass
from pathlib import Path

@dataclass
class SurveyGroup:
    id: int
    files: list[Path]

# Generujemy Literale dynamicznie – dla uproszczenia pozostawiamy jawne typy,
# ale walidację i normalizację oprzemy na specyfikacjach.

class MedicalSurvey(BaseModel):
    # Wszystkie pola zdefiniowane w field_specs – dla czytelności wypisujemy je jawnie,
    # ale wartości domyślne i walidację bierzemy ze specyfikacji.

    # A. Demografia
    plec: Optional[str] = None
    wiek: Optional[int] = Field(default=None, ge=18, le=80)
    miejsce_zamieszkania: Optional[str] = None
    stan_cywilny: Optional[str] = None
    forma_zamieszkania: Optional[str] = None
    stopien_studiow: Optional[str] = None
    uczelnia: str = ""

    # B. Aktywność zawodowa
    praca_status: Optional[str] = None
    praca_system: str = ""
    oddzial: Optional[str] = None
    staz_pracy: str = ""

    # C. Styl życia
    sen_godziny: Optional[str] = None
    ekran_godziny: Optional[str] = None
    kofeina: Optional[str] = None

    # D. Objawy (21)
    objaw_mniej_uwazna: Optional[str] = None
    objaw_trudno_skupic: Optional[str] = None
    objaw_trudno_myslec: Optional[str] = None
    objaw_niezdarna: Optional[str] = None
    objaw_zapominalska: Optional[str] = None
    objaw_wyznaczac_tempo: Optional[str] = None
    objaw_zmotywowac_fizycznie: Optional[str] = None
    objaw_zmotywowac_spotkania: Optional[str] = None
    objaw_nie_zdolna_poza_domem: Optional[str] = None
    objaw_wysilek_fizyczny: Optional[str] = None
    objaw_trudnosci_decyzyjne: Optional[str] = None
    objaw_zmusic_do_myslenia: Optional[str] = None
    objaw_miesnie_z_waty: Optional[str] = None
    objaw_dyskomfort_fizyczny: Optional[str] = None
    objaw_ukonczenie_myslenie: Optional[str] = None
    objaw_uporzadkowanie_mysli: Optional[str] = None
    objaw_ukonczenie_wysilek: Optional[str] = None
    objaw_myslenie_spowolnione: Optional[str] = None
    objaw_problemy_koncentracja: Optional[str] = None
    objaw_ograniczyc_aktywnosc: Optional[str] = None
    objaw_czesciej_odpoczywac: Optional[str] = None

    # E. Stan zdrowia
    anemia: Optional[str] = None
    problemy_tarczyca: Optional[str] = None
    jaka_tarczyca: str = ""
    inne_choroby: str = ""

    # F. Jakość snu
    zasypianie: Optional[str] = None
    budzenie_noc: Optional[str] = None
    budzenie_rano: Optional[str] = None
    czas_snu: Optional[str] = None
    jakosc_snu: Optional[str] = None
    samopoczucie: Optional[str] = None
    sprawnosc: Optional[str] = None
    sennosc: Optional[str] = None

    # G. CES-D (20)
    cesd_przeszkadzaly: Optional[str] = None
    cesd_brak_apetytu: Optional[str] = None
    cesd_chandra: Optional[str] = None
    cesd_tak_samo_dobry: Optional[str] = None
    cesd_ciezko_skoncentrowac: Optional[str] = None
    cesd_przygnebiony: Optional[str] = None
    cesd_wysilek: Optional[str] = None
    cesd_optymistycznie: Optional[str] = None
    cesd_zycie_porazka: Optional[str] = None
    cesd_strach: Optional[str] = None
    cesd_sen_niespokojny: Optional[str] = None
    cesd_szczesliwy: Optional[str] = None
    cesd_mowil_mniej: Optional[str] = None
    cesd_samotny: Optional[str] = None
    cesd_ludzie_nieprzyjazni: Optional[str] = None
    cesd_radosci: Optional[str] = None
    cesd_placzu: Optional[str] = None
    cesd_smutno: Optional[str] = None
    cesd_ludzie_nie_lubia: Optional[str] = None
    cesd_nic_nie_zabrac: Optional[str] = None

    # H. Metadane
    needs_review: dict[str, bool] = {}

    # --- Walidacja i normalizacja ---
    @field_validator("*", mode="before")
    @classmethod
    def normalize_field(cls, v, info):
        field_name = info.field_name
        if field_name == "needs_review":
            return v
        spec = FIELD_SPEC_BY_NAME.get(field_name)
        if not spec:
            return v
        # Jeśli to select, sprawdź czy wartość jest w dozwolonych
        if spec.kind == "select":
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
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [ts]
        for f in ALL_FIELDS:
            val = getattr(self, f.name, "")
            row.append(str(val) if val is not None else "")
        return row

    @classmethod
    def from_ai_json(cls, data: dict) -> "MedicalSurvey":
        kwargs = {}
        for f in ALL_FIELDS:
            raw = data.get(f.name)
            # Dla wieku wyciągnij liczbę
            if f.name == "wiek" and isinstance(raw, (int, str)):
                if isinstance(raw, str):
                    import re
                    m = re.search(r"\d+", raw)
                    raw = int(m.group()) if m else None
            kwargs[f.name] = raw
        kwargs["needs_review"] = data.get("needs_review", {})
        return cls(**kwargs)