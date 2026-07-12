# RAPORT STANU PROJEKTU: AnkieterAI

**Data:** 2026-07-12  
**Branch:** main (up-to-date z origin/main)  
**Git status:** clean

---

## 🏗️ Struktura i Stack

- **Stack:** Python 3.12+, Streamlit, Ollama (deepseek-ocr + llama3.1), Cloudflared Tunnel
- **Architektura:** Modularna - `src/` z 8 modułami, `scripts/` z 5 skryptami PS1, `tests/` 6 plików
- **AI Architecture:** Producer-Consumer (VLM → Text LLM), auto-fallback sekwencyjny przy VRAM OOM

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

### Etap 3 — Przebudowa Architektury AI na Producer-Consumer

| Krok | Opis | Status |
|------|------|--------|
| 1 | Rozszerzenie `config.py` o `vlm_model`, `text_model`, `ollama_num_parallel` | ✅ |
| 2 | Prompty z placeholderami (`build_vlm_prompt`, `build_text_format_prompt`) | ✅ |
| 3 | Przebudowa `client.py` — `_extract_text_vlm`, `_format_json_llm`, producer-consumer, fallback | ✅ |
| 4 | Nowe statusy w `ProcessingStatus` (vlm_extracting, text_formatting, fallback_activated) | ✅ |
| 5 | Aktualizacja UI processing — obsługę nowych statusów | ✅ |
| 6 | Usunięcie `_analyze_page()`, aktualizacja importów | ✅ |
| 7 | Nowe testy — 15/15 passed | ✅ |
| 8 | Walidacja kompatybilności | ✅ |

---

## 📦 STAN MODUŁÓW ŹRÓDŁOWYCH (`src/`)

| Plik | Linii | Status | Uwagi |
|------|-------|--------|-------|
| `config.py` | 21 | ✅ | Pydantic Settings, env prefix `ANKIETER_`, dual model config |
| `schemas.py` | 470 | ✅ | 67 pól MedicalSurvey, CSV mapping, needs_review, normalizacja |
| `state_manager.py` | 90 | ✅ | Session state wrapper, auth, progress, AI results cache |
| `data_handler.py` | 78 | ✅ | Grupowanie po 5, CSV z BOM, JSON cache |
| `ai/client.py` | ~350 | ✅ | Producer-consumer, dual-model (VLM + Text LLM), auto-fallback |
| `ai/prompts.py` | 57 | ✅ | build_system_prompt + build_vlm_prompt + build_text_format_prompt |
| `ui/pages/processing.py` | 83 | ✅ | Obsługa statusów VLM/TextLLM, spinery, fallback |
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
| **11** | **KRYTYCZNY: UI rozjeżdża się przy interakcji z kontrolką** | ❌ Otwarte | **Krytyczny** |

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
- **Etap 1:** Pre-processing obrazów (resize, grayscale, contrast), `keep_alive: "-1"`, `temperature: 0` ✅ ZROBIONE
- **Etap 2:** Architektura dwuetapowa (VLM → tekst → Text LLM → JSON) ✅ ZROBIONE
- **Etap 3:** Async producer-consumer z `asyncio.Queue` ✅ ZROBIONE
- **Etap 4:** LangSmith tracing