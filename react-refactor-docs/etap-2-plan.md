# Etap 2 — Port warstwy domain

## Cel

Doprowadzenie warstwy domain i AI do pełnej niezależności od Streamlitu, przygotowanie ich do wywołania z async workera FastAPI. Usunięcie konceptu `needs_review` zgodnie z decyzją z Etapu 0.

---

## Analiza obecnego stanu

### Co już działa (po Etapie 1)

| Moduł | Status | Zależność od Streamlit |
|-------|--------|----------------------|
| `domain/field_specs.py` | Gotowy | Brak |
| `domain/schemas.py` | Wymaga zmian | Brak (ale ma `needs_review`) |
| `domain/csv_export.py` | Gotowy | Brak |
| `ai/client.py` | Wymaga zmian | Brak (ale ma `needs_review`) |
| `ai/prompts.py` | Gotowy | Brak |
| `ai/tracing.py` | Gotowy | Brak |
| `ingestion/file_grouping.py` | Gotowy | Brak |
| `config.py` | Gotowy | Brak |
| `logger.py` | Gotowy | Brak |
| `data_handler.py` | Gotowy | Brak |

### Kluczowe spostrzeżenia

1. **`ai/client.py` jest już w pełni async** — używa `httpx.AsyncClient`, wszystkie metody to `async def`. Nie wymaga znaczących zmian architektonicznych do pracy z FastAPI async workerem.

2. **Callback pattern jest generyczny** — `Callable[[ProcessingStatus], None]` nie jest powiązany ze Streamlitem. Worker w Etapie 3 może wstrzyknąć własny callback.

3. **Jedyny moduł AI/domain z zależnością od Streamlit** — brak. Wszystkie moduły importują się czysto.

4. **`needs_review` występuje w 3 plikach** — `schemas.py` (definicja), `ai/client.py` (merge), testy.

---

## Zakres zmian

### Zmiana 1: Usunięcie `needs_review` z `domain/schemas.py`

**Plik:** `src/domain/schemas.py`

| Linia | Obecny kod | Nowy kod |
|-------|-----------|----------|
| 100 | `needs_review: dict[str, bool] = {}` | Usunięcie linii |
| 107-108 | `if field_name == "needs_review": return v` | Usunięcie warunku (niepotrzebny — pole nie istnieje) |
| 159 | `kwargs["needs_review"] = data.get("needs_review", {})` | Usunięcie linii |

**Efekt:** `MedicalSurvey` nie będzie miał pola `needs_review`. Normalizator nie będzie pomijał żadnych pól. `from_ai_json()` nie będzie forsował tego klucza.

---

### Zmiana 2: Usunięcie merge'owania `needs_review` z `ai/client.py`

**Plik:** `src/ai/client.py`

| Linia | Obecny kod | Nowy kod |
|-------|-----------|----------|
| 460 | `needs_review = {}` | Usunięcie linii |
| 464 | `review = part.pop("needs_review", {}) or {}` | Usunięcie linii |
| 465 | `needs_review.update(review)` | Usunięcie linii |
| 469 | `merged["needs_review"] = needs_review` | Usunięcie linii |
| 478 | `result_dict["needs_review"] = validated.needs_review` | Usunięcie linii |

**Efekt:** `analyze_survey()` zwróci czysty słownik z 63 polami, bez metadanych `needs_review`.

---

### Zmiana 3: Aktualizacja testów

**Plik:** `tests/conftest.py`

| Linia | Obecny kod | Nowy kod |
|-------|-----------|----------|
| 170 | `"needs_review": {"p2_wiek": True, "p7_uczelnia": False},` | Usunięcie linii |

**Plik:** `tests/test_schemas.py`

| Linia | Obecny kod | Nowy kod |
|-------|-----------|----------|
| 14 | `assert survey.needs_review["p2_wiek"] is True` | Usunięcie asercji (pole nie istnieje) |

---

### Zmiana 4: Weryfikacja czystości importów

Brak zmian w kodzie — tylko weryfikacja, że:

- `domain/schemas.py` importuje się bez `streamlit`
- `domain/field_specs.py` importuje się bez `streamlit`
- `domain/csv_export.py` importuje się bez `streamlit`
- `ai/client.py` importuje się bez `streamlit`
- `ai/prompts.py` importuje się bez `streamlit`
- `ai/tracing.py` importuje się bez `streamlit`

**Wynik analizy:** Wszystkie moduły domain/ai są już wolne od Streamlita. Zmiana 1-2 to jedyne modyfikacje kodu.

---

## Kolejność implementacji

| # | Plik | Zależności | Weryfikacja |
|---|------|-----------|-------------|
| 1 | `src/domain/schemas.py` | — | Usunięcie `needs_review` z modelu, walidatora, `from_ai_json()` |
| 2 | `src/ai/client.py` | `schemas.py` | Usunięcie merge'owania `needs_review` z `analyze_survey()` |
| 3 | `tests/conftest.py` | `schemas.py` | Usunięcie `needs_review` z fixture |
| 4 | `tests/test_schemas.py` | `conftest.py` | Usunięcie asercji na `needs_review` |
| 5 | Weryfikacja importów | — | `python -c "from domain.schemas import MedicalSurvey"` itd. |
| 6 | Uruchomienie testów | Wszystkie | `pytest tests/` |

---

## Decyzje projektowe

| Pytanie | Decyzja | Uzasadnienie |
|---------|---------|-------------|
| Czy `needs_review` ma zniknąć całkowicie? | Tak | Decyzja z Etapu 0 (#7): "całkowicie usuwamy mechanizmy needs_review" |
| Czy `ai/client.py` wymaga zmian architektonicznych? | Nie | Jest już w pełni async, callback jest generyczny |
| Czy `data_handler.py` wymaga zmian? | Nie | JSON cache jest framework-agnostic, wystarczy dla workera |
| Czy dodajemy `__init__.py`? | Nie | `sys.path.insert` w `main.py` wystarcza, nie komplikujemy |

---

## Kryteria akceptacji

- [ ] `MedicalSurvey` nie ma pola `needs_review`
- [ ] `MedicalSurvey.from_ai_json()` nie generuje `needs_review`
- [ ] `AIClient.analyze_survey()` nie merge'uje `needs_review`
- [ ] `AIClient.analyze_survey()` zwraca dict z 63 polami (bez metadanych)
- [ ] `pytest tests/` — wszystkie testy przechodzą
- [ ] `python -c "from domain.schemas import MedicalSurvey"` — import bez błędów
- [ ] `python -c "from ai.client import AIClient"` — import bez błędów
- [ ] Żaden moduł w `domain/` i `ai/` nie importuje `streamlit`

---

## Uwagi

1. **Backward compatibility cache** — istniejący `logs/cache_results.json` może zawierać `needs_review`. W Etapie 3 worker powinien to obsługiwać (ignorować lub czyścić przy odczycie).

2. **Stary Streamlit UI** — `app.py` i `ui/verification.py` używają `needs_review` do podświetlania pól. To nie jest problem — stary kod zostanie usunięty w Etapie 10. Na razie oba runtime (Streamlit + FastAPI) współistnieją.

3. **Test `to_csv_row` assertuje 71 elementów** — to się nie zmienia (1 timestamp + 63 pola + 7 placeholderowych? — do weryfikacji przy okazji, ale poza zakresem Etapu 2).
