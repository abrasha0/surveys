# RAPORT STANU PROJEKTU: AnkieterAI

**Data:** 2026-07-11  
**Branch:** main (up-to-date z origin/main)  
**Git status:** clean

---

## 🏗️ Struktura i Stack

- **Stack:** Python 3.12+, Streamlit, Ollama (deepseek-ocr), Cloudflared Tunnel
- **Architektura:** Modularna - `src/` z 8 modułami, `scripts/` z 5 skryptami PS1, `tests/` 6 plików

---

## ✅ ZREALIZOWANE FAZY (zgodnie z `docs/implementation-plan.md`)

| Faza | Opis | Status |
|------|------|--------|
| 0 | Środowisko: requirements.txt, .gitignore, config.toml | ✅ Zrobione |
| 1 | `scripts/setup_env.ps1` | ✅ Zrobione |
| 2 | `scripts/setup_ollama.ps1` | ✅ Zrobione |
| 3 | Fundament: `config.py`, `state_manager.py`, `main.py` (login) | ✅ Zrobione |
| 4 | Schemat i dane: `schemas.py`, `data_handler.py` | ✅ Zrobione |
| 5 | AI Client: `ai_client.py` (batch, per-page, cache, retry, logging) | ✅ Zrobione |
| 6 | UI Components: `ui_components.py` (side-by-side, zoom, tabs, Spacja) | ✅ Zrobione |
| 7 | Spięcie logiki: `main.py` (routing, upload→batch→verify→CSV) | ✅ Zrobione |
| 8 | Deployment: `run_dev.ps1`, `deploy_tunnel.ps1`, `full_setup.ps1` | ⚠️ Większość OK, `deploy_tunnel.ps1` ma bugi |
| 9 | Testy: 58 testów (56 ✅, 2 ❌) | ⚠️ 2 testy fail |

---

## 📦 STAN MODUŁÓW ŹRÓDŁOWYCH (`src/`)

| Plik | Linii | Status | Uwagi |
|------|-------|--------|-------|
| `config.py` | 18 | ✅ | Pydantic Settings, env prefix `ANKIETER_` |
| `schemas.py` | 470 | ✅ | 67 pól MedicalSurvey, CSV mapping, needs_review, normalizacja |
| `state_manager.py` | 90 | ✅ | Session state wrapper, auth, progress, AI results cache |
| `data_handler.py` | 78 | ✅ | Grupowanie po 5, CSV z BOM, JSON cache |
| `ai_client.py` | 461 | ✅ | Per-page prompts, retry 3x, async batch, progress callback, logging |
| `ui_components.py` | 439 | ✅ | Side-by-side, 5 tabs, zoom (CSS), red dot dla needs_review, Spacja shortcut |
| `main.py` | 130 | ✅ | Routing: login → upload → batch AI → verify → CSV → complete |
| `logger.py` | 57 | ✅ | File + console, DEBUG, noise reduction |
| `__init__.py` | 0 | ✅ | Pusty |

---

## 🐛 OTWARTE ISSUES (`docs/known-issues.md`)

| # | Opis | Status | Priorytet |
|---|------|--------|-----------|
| 3.1 | Rozszerzenie logowania o request/response per-call | ❌ Otwarte | Średni |
| 7 | Lepsze komunikaty przy `JSONDecodeError` (treść odpowiedzi, status HTTP) | ❌ Otwarte | Średni |
| 9 | Monitoring issues w repo (tagi commitów + sekcja README/plik) | ❌ Otwarte | Niski |
| 10 | Progress bar: reset po kliknięciu "Rozpocznij analizę" | ❌ Otwarte | Średni |
| **11** | **KRYTYCZNY: UI rozjeżdża się przy interakcji z kontrolką (zakładki rozjeżdżają, powrót do Strony 1 naprawia)** | ❌ Otwarte | **Krytyczny** |

**Zamknięte (✅):** #1 (sync tabs), #2 (progress UI), #3 (debug log), #4 (file log), #5 (brak domyślnych wartości), #6 (czerwona kropka znika po interakcji), #7 (Strona 1 - 2 kolumny 1-14).

---

## ❌ FAILING TESTY (2/58)

```bash
FAILED tests/test_schemas.py::TestExtractAge::test_no_number_fallback 
  # _extract_age("nie wiem") zwraca None, test oczekuje 22 (stary fallback)

FAILED tests/test_schemas.py::TestNormalizeValue::test_literal_fallback_to_first
  # _normalize_value("plec", "Nieznane") zwraca None, test oczekuje "Kobieta"
```

**Przyczyna:** Zmieniono logikę `_normalize_value` - teraz zwraca `None` zamiast `choices[0]` dla nieznanych wartości (issue #5 "Usunięcie domyślnych wartości"). Testy nie zostały zaktualizowane.

---

## ⚠️ PROBLEMY W SKRYPTACH DEPLOYMENTOWYCH

**`scripts/deploy_tunnel.ps1` - BUGI:**
- Linia 106: `$cfPath` używane przed zdefiniowaniem (powinno być `$CloudflaredPath`)
- Linia 125: `$TunnelUrlFile` niezdefiniowane (powinno być `$TunnelUrlFile` zdefiniowane wcześniej)
- Brak parametryzacji ścieżek

---

## 📋 README.md - STAN

Minimalny - brakuje:
- Szczegółowego opisu architektury modułów
- Opisu flow użytkownika (side-by-side, zoom, Spacja)
- Troubleshootingu (Ollama, cache, CSV BOM)
- Informacji o znanych issue'ach (#11 krytyczny)

---

## 🎯 CO MOŻEMY ZROBIĆ TERAZ (KOLEJNE KROKI)

### Priorytet 1 - KRYTYCZNE (Issue #11)
> **Analiza i naprawa rozjeżdżania UI przy interakcji z formularzem**
- Wymaga głębokiej analizy `ui_components.py` (CSS, tabs, columns, rerun behavior)
- Może dotyczyć: `st.columns` w pętli, `st.tabs` state, CSS `transform: scale`, `st.rerun()` przy submit

### Priorytet 2 - NAPRAWY TESTÓW
- Zaktualizować 2 failujące testy w `test_schemas.py` do nowej logiki (None zamiast fallbacku)

### Priorytet 3 - DEPLOYMENT
- Naprawić `deploy_tunnel.ps1` (zmienne `$cfPath`, `$TunnelUrlFile`)

### Priorytet 4 - DOKUMENTACJA
- Rozszerzyć README o: architekturę, UX flow, troubleshooting, known issues
- Dodać tracking issues do README (issue #9)

### Priorytet 5 - OPTYMALIZACJA (z `docs/optimalization-plan.md`)
- **Etap 1:** Pre-processing obrazów (resize, grayscale, contrast), `keep_alive: "-1"`, `temperature: 0`
- **Etap 2:** Architektura dwuetapowa (VLM → tekst → Text LLM → JSON)
- **Etap 3:** Async producer-consumer z `asyncio.Queue`
- **Etap 4:** LangSmith tracing

> ⚠️ **UWAGA z optimalization-plan.md:** "Kategoryczny zakaz modyfikowania promptów w kodzie - prompty z zewnętrznego modułu/konfiguracji"

---

## 🤔 PYTANIA DECYZYJNE

1. **Issue #11 (krytyczny UI)** - chcesz, żebym przeanalizowałem `ui_components.py` i przygotowałem plan naprawy jako osobny task?

2. **Testy** - naprawiam 2 failujące testy (to prosta zmiana asercji), czy robimy to teraz?

3. **Deployment tunnel** - naprawiam `deploy_tunnel.ps1`?

4. **Optymalizacja (Etap 1-4)** - to duży refaktoring `ai_client.py` + nowa architektura. Chcesz przejść do fazy optymalizacji, czy najpierw stabilizujemy obecny stan?

5. **README** - rozszerzamy teraz, czy na końcu?