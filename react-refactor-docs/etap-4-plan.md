# Etap 4 — Endpoint zapisu + zgodność formatu CSV

**Zależności:** Etap 2, Etap 3.

---

## Cel

Implementacja `POST /api/surveys/{id}/save` — endpointu walidującego dane z
weryfikacji użytkownika, zapisującego wiersz do CSV zgodnie z ustalonym formatem,
ustawiającego status ankiety na `verified` oraz czyszczącego result z pamięci.
Dodatkowo weryfikacja pełnej kompatybilności `csv_export.py` z docelowym formatem
kolumna-po-kolumnie.

---

## Decyzje potwierdzone

| Decyzja | Status |
|---------|--------|
| Force save (zatwierdź mimo błędów) | **TAK** — zostaje |
| Czyszczenie result po save | **TAK** — `survey.result = None` po zapisie |

---

## Istniejące zasoby (co już działa)

| Zasób | Status | Uwagi |
|-------|--------|-------|
| `domain/csv_export.py:save_survey_to_csv()` | Działa | Append mode, UTF-8-BOM, header tworzony jednorazowo |
| `domain/csv_export.py:CSV_HEADER` | Działa | 71 kolumn (1 timestamp + 70 pól z `ALL_FIELDS`) |
| `domain/schemas.py:MedicalSurvey.to_csv_row()` | Działa | Zwraca listę 71 elementów |
| `domain/schemas.py:MedicalSurvey.normalize_field()` | Działa | Walidacja select/number/text |
| `domain/field_specs.py:ALL_FIELDS` | Źródło prawdy | 70 pól, 5 stron |
| `data_handler.py:export_csv_path()` | Działa | Zwraca `config.app["csv_results"]` = `"wyniki.csv"` |
| Worker state (`SurveyState.status`) | Brak `verified` | Do dodania |
| `POST /api/surveys/{id}/save` | Stub (501) | Do implementacji |

---

## Rozbieżność w dokumentacji

`docs/survey-structure.md` mówi o **63 polach** i **68 nagłówkach CSV**, ale
rzeczywista implementacja w `field_specs.py` ma **70 pól** i **71 nagłówków CSV**.
Rozbieżność wynika z pominięcia pól tekstowych "inne" (`p5_inne`, `p9_inne`,
`p10_inne`, `tarczyca_jakie`, `choroba_inne`) oraz błędnych nazw pól
(dokumentacja używa `plec`, `wiek` zamiast `p1_plec`, `p2_wiek`).
Źródłem prawdy jest `field_specs.py`.

---

## Nowa struktura plików

Brak nowych plików — modyfikujemy istniejące:

```
src/
├── worker/state.py              # Dodanie statusu "verified" + mark_verified()
├── routers/api.py               # Implementacja POST /surveys/{id}/save

tests/
└── test_save_endpoint.py        # Nowy plik testów
```

---

## Krok 1: `src/worker/state.py` — Status `verified`

**Cel:** Rozszerzenie `SurveyState.status` o nowy status `verified` po zapisie do CSV.

### Zmiany w `is_finished()`

```python
# PRZED:
def is_finished(self) -> bool:
    return all(s.status in ("ready", "error") for s in self.surveys)

# PO:
def is_finished(self) -> bool:
    return all(s.status in ("ready", "error", "verified") for s in self.surveys)
```

### Nowa metoda `mark_verified()` (po `set_survey_status`)

```python
def mark_verified(self, survey_id: int):
    survey = self.surveys[survey_id]
    if survey.status != "ready":
        raise ValueError(f"Cannot verify survey in status '{survey.status}'")
    survey.status = "verified"
    survey.result = None  # Wyczyść result po zapisie do CSV
```

Status ankiety przyjmuje teraz wartości:
```
queued | processing | ready | error | verified
```

---

## Krok 2: `src/routers/api.py` — Implementacja endpointu save

**Cel:** Kompletna implementacja `POST /api/surveys/{survey_id}/save`.

### Specyfikacja endpointu

```
POST /api/surveys/{survey_id}/save
Content-Type: application/json
Authorization: cookie (get_current_user)

Body:
{
    "values": { ... },
    "force": false
}

Response 200:
{
    "status": "saved",
    "survey_id": 0,
    "csv_path": "wyniki.csv"
}

Response 400:
{
    "detail": "Survey not in 'ready' status"
}

Response 422:
{
    "detail": {
        "message": "Validation errors",
        "errors": { "field_name": "error message", ... }
    }
}

Response 404:
{
    "detail": "Survey not found"
}
```

### Nowe importy (dodaj na górze pliku)

```python
from pydantic import BaseModel, ValidationError
from typing import Optional
from domain.schemas import MedicalSurvey
from domain.field_specs import ALL_FIELDS, FIELD_SPEC_BY_NAME
from domain.csv_export import save_survey_to_csv
from data_handler import export_csv_path
```

### Model request body

```python
class SaveRequest(BaseModel):
    values: dict
    force: Optional[bool] = False
```

### Implementacja endpointu

Zamień istniejący stub (zwraca 501) na:

```python
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

    # Normalizacja wartości pól
    normalized = {}
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
            else:
                normalized[f.name] = None
        elif spec and spec.kind == "number":
            try:
                normalized[f.name] = int(raw) if raw is not None else None
            except (ValueError, TypeError):
                normalized[f.name] = None
        elif spec and spec.kind == "text":
            normalized[f.name] = str(raw).strip() if raw is not None else ""
        else:
            normalized[f.name] = raw

    # Walidacja przez MedicalSurvey
    validation_errors = {}
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

    # Nawet przy force — używamy znormalizowanych danych
    if validation_errors and request.force:
        survey_data = MedicalSurvey(**normalized)

    # Zapis do CSV
    csv_path = export_csv_path()
    save_survey_to_csv(survey_data, csv_path)

    # Aktualizuj status na "verified" + wyczyść result
    worker.state.mark_verified(survey_id)

    logger.info("Survey %d saved to CSV: %s", survey_id, csv_path)
    return {
        "status": "saved",
        "survey_id": survey_id,
        "csv_path": csv_path,
    }
```

### Kluczowe szczegóły implementacyjne

1. **Normalizacja jest JEDNA** — niezależnie od `force`. Różnica: bez force
   zwracamy 422 przy błędach, z force zapisujemy mimo błędów.

2. **Case-insensitive match** dla select values — tak samo jak w
   `MedicalSurvey.normalize_field()`. Duplikacja logiki, ale celowa — endpoint
   nie polega na Pydantic validatorze.

3. **`survey.result = None`** w `mark_verified()` — czyści pamięć po zapisie.
   Frontend trzyma swoje dane w React state, więc nie tracimy nic.

4. **Logowanie** — `logger.info()` po zapisie do CSV dla audytu.

---

## Krok 3: `tests/test_save_endpoint.py` — Testy

### Fixtures

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from main import app
from worker import get_worker
from worker.state import SurveyState
from pathlib import Path


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    client.post("/api/auth/login", json={"password": ""})
    return client


@pytest.fixture
def worker_with_ready_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="ready",
                     result={"p1_plec": "Kobieta", "p2_wiek": 22}),
    ]
    worker.state.global_state.total = 1
    worker.state.global_state.processed = 1
    return worker


@pytest.fixture
def worker_with_processing_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="processing"),
    ]
    return worker


@pytest.fixture
def worker_with_queued_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="queued"),
    ]
    return worker


@pytest.fixture
def worker_with_error_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="error",
                     error_message="OCR failed"),
    ]
    return worker


@pytest.fixture
def worker_with_verified_survey():
    worker = get_worker()
    worker.state.surveys = [
        SurveyState(id=0, files=[Path("test.jpg")], status="verified"),
    ]
    return worker


SAMPLE_VALUES = {
    "p1_plec": "Kobieta",
    "p2_wiek": 23,
    "p3_miejsce": "Wieś",
    "p4_stan": "Panna/kawaler",
    "p5_forma": "Z rodziną",
    "p5_inne": "",
    "p6_stopien": "Studia I stopnia",
    "p7_uczelnia": "PANS",
    "p8_praca": "Nie (Jeśli zaznaczyłaś/eś tą odpowiedź, przejdź do pytania nr 12)",
    "p9_system": None,
    "p9_inne": "",
    "p10_oddzial": None,
    "p10_inne": "",
    "p11_staz": "",
    "p12_sen": "7-8 godzin",
    "p13_ekran": "Powyżej 3 godzin",
    "p14_kofeina": "Tak, 1-2 porcje dziennie",
    "mfis_1": "2", "mfis_2": "3", "mfis_3": "1", "mfis_4": "0",
    "mfis_5": "2", "mfis_6": "1", "mfis_7": "3", "mfis_8": "0",
    "mfis_9": "0", "mfis_10": "1", "mfis_11": "2", "mfis_12": "1",
    "mfis_13": "0", "mfis_14": "2", "mfis_15": "1", "mfis_16": "2",
    "mfis_17": "0", "mfis_18": "1", "mfis_19": "3", "mfis_20": "0",
    "mfis_21": "1",
    "choroba_anemia": "NIE",
    "choroba_tarczyca": "NIE",
    "tarczyca_jakie": "",
    "choroba_inne": "",
    "sen_1": "szybkie", "sen_2": "nie występuje",
    "sen_3": "o zamierzonej godzinie", "sen_4": "wystarczający",
    "sen_5": "satysfakcjonująca", "sen_6": "dobre",
    "sen_7": "niezaburzona", "sen_8": "nie zdarza się",
    "depr_1": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_2": "Przez niedługi czas (1-2 dni)",
    "depr_3": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_4": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_5": "Przez niedługi czas (1-2 dni)",
    "depr_6": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_7": "Przez niedługi czas (1-2 dni)",
    "depr_8": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_9": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_10": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_11": "Przez niedługi czas (1-2 dni)",
    "depr_12": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_13": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_14": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_15": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_16": "Czasem lub przez umiarkowany okres (3-4 dni)",
    "depr_17": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_18": "Przez niedługi czas (1-2 dni)",
    "depr_19": "Rzadko lub wcale (mniej niż 1 dzień)",
    "depr_20": "Rzadko lub wcale (mniej niż 1 dzień)",
}
```

### Test cases

```python
class TestSaveEndpointHappyPath:
    def test_save_ready_survey_returns_200(self, auth_client, worker_with_ready_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 200
        assert response.json()["status"] == "saved"

    def test_save_creates_csv_row(self, auth_client, worker_with_ready_survey, tmp_path):
        from config import config
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_output.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            assert csv_path.exists()
            content = csv_path.read_text(encoding="utf-8-sig")
            assert "Kobieta" in content
        finally:
            config.app["csv_results"] = orig

    def test_save_sets_verified_status(self, auth_client, worker_with_ready_survey):
        auth_client.post("/api/surveys/0/save",
                          json={"values": SAMPLE_VALUES})
        worker = get_worker()
        assert worker.state.get_survey_state(0).status == "verified"

    def test_save_clears_result_from_memory(self, auth_client, worker_with_ready_survey):
        worker = get_worker()
        assert worker.state.get_survey_state(0).result is not None
        auth_client.post("/api/surveys/0/save",
                          json={"values": SAMPLE_VALUES})
        assert worker.state.get_survey_state(0).result is None


class TestSaveEndpointValidation:
    def test_save_without_force_returns_422_on_errors(self, auth_client, worker_with_ready_survey):
        bad_values = SAMPLE_VALUES.copy()
        bad_values["p1_plec"] = "NieznanaWartosc"
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": bad_values})
        assert response.status_code == 422
        assert "errors" in response.json()["detail"]

    def test_save_force_with_validation_errors_returns_200(self, auth_client, worker_with_ready_survey):
        bad_values = SAMPLE_VALUES.copy()
        bad_values["p1_plec"] = "NieznanaWartosc"
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": bad_values, "force": True})
        assert response.status_code == 200
        assert response.json()["status"] == "saved"

    def test_save_force_writes_none_for_invalid_select(self, auth_client, worker_with_ready_survey, tmp_path):
        from config import config
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_force.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            bad_values = SAMPLE_VALUES.copy()
            bad_values["p1_plec"] = "NieznanaWartosc"
            auth_client.post("/api/surveys/0/save",
                              json={"values": bad_values, "force": True})
            content = csv_path.read_text(encoding="utf-8-sig")
            # None is written as empty string in CSV
            rows = list(csv.reader(content.strip().split("\n")))
            assert len(rows) == 2  # header + data
        finally:
            config.app["csv_results"] = orig


class TestSaveEndpointEdgeCases:
    def test_save_nonexistent_survey_returns_404(self, auth_client, worker_with_ready_survey):
        response = auth_client.post("/api/surveys/999/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 404

    def test_save_processing_survey_returns_400(self, auth_client, worker_with_processing_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400

    def test_save_queued_survey_returns_400(self, auth_client, worker_with_queued_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400

    def test_save_error_survey_returns_400(self, auth_client, worker_with_error_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400

    def test_save_already_verified_returns_400(self, auth_client, worker_with_verified_survey):
        response = auth_client.post("/api/surveys/0/save",
                                     json={"values": SAMPLE_VALUES})
        assert response.status_code == 400


class TestSaveEndpointCSVFormat:
    def test_save_csv_has_bom_encoding(self, auth_client, worker_with_ready_survey, tmp_path):
        from config import config
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_bom.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
        finally:
            config.app["csv_results"] = orig

    def test_save_csv_has_correct_column_count(self, auth_client, worker_with_ready_survey, tmp_path):
        import csv as csv_mod
        from config import config
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_cols.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv_mod.reader(f)
                rows = list(reader)
                assert len(rows[0]) == 71  # header
                assert len(rows[1]) == 71  # data row
        finally:
            config.app["csv_results"] = orig

    def test_save_csv_header_written_once(self, auth_client, worker_with_ready_survey, tmp_path):
        import csv as csv_mod
        from config import config
        from worker.state import SurveyState
        orig = config.app["csv_results"]
        csv_path = tmp_path / "test_once.csv"
        config.app["csv_results"] = str(csv_path)
        try:
            # Add second ready survey
            worker = get_worker()
            worker.state.surveys.append(
                SurveyState(id=1, files=[Path("test2.jpg")], status="ready",
                             result={"p1_plec": "Mężczyzna"})
            )
            auth_client.post("/api/surveys/0/save",
                              json={"values": SAMPLE_VALUES})
            auth_client.post("/api/surveys/1/save",
                              json={"values": SAMPLE_VALUES})
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv_mod.reader(f)
                rows = list(reader)
                # Header + 2 data rows, not 2 headers
                assert rows[0][0] == "Sygnatura czasowa"
                assert rows[1][0] != "Sygnatura czasowa"
                assert rows[2][0] != "Sygnatura czasowa"
                assert len(rows) == 3
        finally:
            config.app["csv_results"] = orig
```

---

## Kolejność implementacji

| Krok | Plik | Zależności | Opis |
|------|------|------------|------|
| 1 | `src/worker/state.py` | brak | Dodanie statusu `verified` + metoda `mark_verified()` |
| 2 | `src/routers/api.py` | krok 1 | Importy + `SaveRequest` + `save_survey()` |
| 3 | `tests/test_save_endpoint.py` | kroki 1, 2 | 14 test cases |

---

## Kryteria akceptacji

1. `POST /api/surveys/{id}/save` z poprawnymi danymi zapisuje wiersz do CSV i zwraca `{"status": "saved"}`
2. Po zapisie status ankiety zmienia się z `ready` na `verified`
3. `result` jest `None` po save (wyczyszczony z pamięci)
4. Zapisany wiersz CSV zgadza się z docelowym formatem (71 kolumn, UTF-8-BOM, poprawne nagłówki)
5. Force save pomija błędy walidacji i zapisuje dane znormalizowane
6. Brak force przy błędach walidacji zwraca 422 z listą błędów
7. Ankieta w statusie innym niż `ready` nie może być zapisana (400)
8. Nieistniejąca ankieta zwraca 404

## How to verify

1. **Uruchom serwer:** `.venv\Scripts\Activate.ps1; cd src; uvicorn main:app --reload`
2. **Zaloguj się:** `POST /api/auth/login` → cookie
3. **Przetwórz ankietę:** `POST /api/processing/start` → poczekaj na status `ready`
4. **Pobierz wynik:** `GET /api/surveys/0/result` → `{"result": {...}}`
5. **Zapisz:** `POST /api/surveys/0/save` → `{"status": "saved"}`
6. **Sprawdź status:** `GET /api/surveys` → status `verified`
7. **Sprawdź CSV:** Otwórz `wyniki.csv` — nowy wiersz z danymi ankiety
8. **Test force save:** Wyślij błędną wartość select + `force: true` → zapisuje się z None
9. **Test walidacji:** Wyślij błędną wartość select bez force → 422 z error details

---

## Kluczowe decyzje implementacyjne

1. **Request body z `values` + `force`**: Frontend wysyła surowe wartości pól
   (po edycji użytkownika) wraz z flagą force. To pozwala frontendowi na pełną
   kontrolę nad danymi.

2. **Ręczna normalizacja zamiast Pydantic**: Normalizacja wartości pól odbywa
   się przed `MedicalSurvey(**normalized)`. To daje pełną kontrolę nad
   case-insensitive matching i obsługą None. Pydantic validator jest backupem
   dla pól numerycznych (zakres wieku).

3. **Status `verified` jako osobny stan**: Nie łączymy z `ready` — to czytelne
   oddzielenie "przetworzone przez AI" od "zatwierdzone przez użytkownika
   i zapisane do CSV".

4. **Czyszczenie result po save**: `survey.result = None` w `mark_verified()`.
   Oszczędza pamięć, a dane są trwale zapisane w CSV.

5. **Brak zmian w `csv_export.py`**: Istniejący kod jest poprawny i kompatybilny.
   Nie komplikujemy go bez potrzeby.

6. **Brak zmian w `field_specs.py`**: 70 pól, 71 kolumn CSV — to jest prawidłowa
   liczba. Dokumentacja (`survey-structure.md`) jest nieaktualna, ale to nie jest
   zakres Etapu 4.
