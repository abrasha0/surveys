# Etap 10 — Cutover i sprzątanie

**Zależności:** wszystkie powyższe, zweryfikowane na realnych ankietach.

---

## Cel

Ostateczne odcięcie starego kodu Streamlit, aktualizacja dokumentacji do nowego stacka (FastAPI + React), dodanie podstawowego ekranu zakończenia, zamknięcie rozstrzygniętych issues, budowa frontendu do `dist/`.

---

## Stan wyjściowy przed Etapem 10

| Warstwa | Co jest gotowe | Co zostało |
|---------|---------------|------------|
| Backend FastAPI | `src/main.py`, `src/auth.py`, `src/routers/api.py`, `src/worker/`, `src/data_handler.py`, `src/config.py`, `src/logger.py` | Wszystkie endpointy zaimplementowane |
| Domain/AI | `src/domain/`, `src/ai/`, `src/ingestion/` | Czyste od Streamlit |
| Frontend React | `src_ui/` — LoginPage, VerificationPanel, ImageViewer, PageTabs, DynamicForm, FieldRenderer, SurveyHeader, ProcessingProgressBar | Brak ekranu zakończenia (F14) |
| Skrypty | `setup_env.ps1`, `run_dev.ps1`, `full_setup.ps1`, `deploy_tunnel.ps1` | Zaktualizowane w Etapie 9 (uvicorn + npm) |
| Stary Streamlit | `src/app.py`, `src/state/`, `src/ui/`, `src/.streamlit/`, `.streamlit/` | **Nadal istnieje — do usunięcia** |
| Config | `requirements.txt` — bez Streamlit; `config.yaml.example` — OK | `config.yaml` wciąż ma `layout: "wide"` |
| dist/ | Stary placeholder z Etapu 1 | **Nie zbudowany z Reacta** |
| Testy | 7 plików testowych (wszystkie Streamlit-era) | Do usunięcia — poza zakresem migracji |

---

## Plan implementacji — 7 kroków

### Krok 1: Usunięcie starego kodu Streamlit

| Ścieżka | Opis |
|---------|------|
| `src/app.py` | Stary entry point Streamlit |
| `src/state/` (cały katalog) | `state_manager.py` — session_state wrapper |
| `src/ui/` (cały katalog) | 5 stron + widgets/styles/shortcuts |
| `src/.streamlit/config.toml` | Streamlit config w src |
| `.streamlit/config.toml` | Streamlit config w root |
| `wyniki.csv` | Stary CSV ze Streamlit ery |
| `logs/cache_results.json` | Stary cache single-file (nieużywany przez nowy per-survey cache) |

**Komenda:**
```powershell
Remove-Item -Path src/app.py, src/state, src/ui, src/.streamlit, .streamlit, wyniki.csv, logs/cache_results.json -Recurse -Force
```

---

### Krok 2: `config.yaml` — usunięcie Streamlit-specific `layout: "wide"`

**Plik:** `config.yaml`

Usunięcie linii `layout: "wide"` z sekcji `app`.

---

### Krok 3: Usunięcie wszystkich testów

Zgodnie z decyzją z Etapu 0 (#11: "Testy automatyczne — poza zakresem migracji"). Stare testy są pisane pod Streamlit i nie są adaptowane do nowego stacka.

| Plik | Opis |
|------|------|
| `tests/conftest.py` | Fixture'y zależne od Streamlit |
| `tests/test_schemas.py` | Testy modeli danych (przestarzałe) |
| `tests/test_data_handler.py` | Testy I/O (przestarzałe) |
| `tests/test_state_manager.py` | Testy usuniętego StateManager |
| `tests/test_save_endpoint.py` | Testy endpointu (przestarzałe) |
| `tests/test_csv_integrity.py` | Testy CSV (przestarzałe) |
| `tests/test_ai_client.py` | Testy klienta AI (przestarzałe) |
| `tests/__pycache__/` | Cache Python |

**Komenda:**
```powershell
Remove-Item -Path tests -Recurse -Force
```

---

### Krok 4: Frontend — podstawowy ekran zakończenia

Nowy komponent + endpoint do pobierania CSV + routing.

#### 4a: Backend — `src/routers/api.py`

Nowy endpoint `GET /api/surveys/export/csv`:

```python
@router.get("/surveys/export/csv")
def export_csv():
    csv_path = export_csv_path()
    if not Path(csv_path).exists():
        raise HTTPException(status_code=404, detail="CSV not yet created")
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="ankiety_wyniki.csv",
        headers={"Content-Type": "text/csv; charset=utf-8"}
    )
```

#### 4b: Frontend — `src_ui/src/features/complete/CompletePage.tsx` (NOWY)

Ekran zakończenia. Wyświetlany, gdy nie ma już ankiet do zweryfikowania.

**Elementy:**
- Ikona/komunikat sukcesu: "Wszystkie ankiety zweryfikowane ✓"
- Przycisk "Pobierz CSV" → `GET /api/surveys/export/csv`
- Przycisk "Nowa sesja" → odświeżenie do `/app` (ponowny skan katalogu)

#### 4c: Frontend — `src_ui/src/features/verification/VerificationPanel.tsx` (EDYCJA)

Dodanie warunku: gdy `clickableSurveys.length === 0` i `isRunning === false` → nawigacja do `/complete`.

#### 4d: Frontend — `src_ui/src/app/App.tsx` (EDYCJA)

Dodanie trasy `/complete`:

```tsx
<Route
  path="/complete"
  element={
    <AuthGuard>
      <CompletePage />
    </AuthGuard>
  }
/>
```

#### 4e: Frontend — `src_ui/src/api/hooks.ts` (EDYCJA)

Dodanie hooka `useExportCsvUrl()` lub funkcji `exportCsvUrl` do API hooks.

---

### Krok 5: Budowa frontendu i aktualizacja `dist/`

```powershell
cd src_ui
npm run build
Copy-Item src_ui/dist/* ..\dist\ -Recurse -Force
```

Zastąpienie starego placeholdera "Frontend wkrótce" zbudowaną aplikacją React.

---

### Krok 6: Aktualizacja dokumentacji

#### `docs/main-doc.md`

- **"Co to jest i po co"** — aktualizacja opisu stacka: FastAPI + React (zamiast Streamlit)
- **"Funkcjonalności"** — dodanie: interleaved verification, globalny worker w tle, lokalny katalog zdjęć; usunięcie Streamlit-specific
- **"Architektura"** — zmiana diagramu na backend+frontend, dodanie workera
- **"Flow użytkownika"** — upload → skanowanie lokalnego katalogu, weryfikacja interleaved
- **"Deployment"** — uvicorn na 8000 + npm build → dist, Cloudflare tunnel
- **"Ograniczenia"** — usunięcie Streamlit-specific

#### `docs/architecture-report.md`

- **"Struktura katalogowa"** — usunięcie `src/state/`, `src/ui/`; dodanie `src/routers/`, `src/worker/`
- **"Warstwy architektury"** — `UI: src_ui/ (React)` zamiast `ui/pages/*`; `STATE: worker/state.py` zamiast `state/state_manager.py`
- **"Maszyna stanów"** — nowy diagram: `UNAUTHENTICATED → AUTHENTICATED → QUEUED → PROCESSING (worker w tle) → READY → VERIFIED → ALL_DONE`
- **"Kluczowe moduły"** — dodanie `worker/`, `routers/api.py`; usunięcie `ui/`, `state/`
- **"Zależności importowe"** — `main.py → routers/api.py`, `routers/api.py → worker, domain`

#### `README.md`

- Sekcja "Funkcjonalności" — dopisanie interleaved verification, globalny worker, lokalny katalog
- Sekcja "Ograniczenia" — usunięcie Streamlit-specific

---

### Krok 7: `known-issues.md` — zamknięcie issues

| # | Opis | Status | Akcja |
|---|------|--------|-------|
| 3 | Przyciski na verification.py — poziom | ✅ Done | Zamknąć — SurveyHeader w React |
| 4 | Etykiety przycisków | ✅ Done | "Poprzednia/Następna/Zatwierdź ankietę" |
| 5 | `needs_review` | ✅ Done | Usunięte z backendu + frontend nie używa |
| 6 | Lokalny cache/wznawianie sesji | ✅ Done | Per-survey JSON cache |
| 7 | Próg re-OCR | ❌ Otwarte | **Odłożone poza zakres migracji** (decyzja #9 z Etapu 0) |
| 8 | Lokalny katalog zdjęć | ✅ Done | `surveys_dir` w config |
| 9 | Walidacja CSV z formatem | ✅ Done | 71 kolumn, UTF-8 BOM |

---

## Kolejność implementacji

| # | Zadanie | Pliki | Typ |
|---|---------|-------|-----|
| 1 | Usunięcie starego kodu Streamlit | `src/app.py`, `src/state/`, `src/ui/`, `src/.streamlit/`, `.streamlit/`, `wyniki.csv`, `logs/cache_results.json` | Delete |
| 2 | `config.yaml` cleanup | `config.yaml` — usunięcie `layout: "wide"` | Edit |
| 3 | Usunięcie testów | `tests/` (cały katalog) | Delete |
| 4a | Backend: endpoint export CSV | `src/routers/api.py` — dodanie `GET /api/surveys/export/csv` | Edit |
| 4b | Frontend: CompletePage | `src_ui/src/features/complete/CompletePage.tsx` | Nowy |
| 4c | Frontend: routing + integracja | `src_ui/src/app/App.tsx`, `src_ui/src/features/verification/VerificationPanel.tsx` | Edit |
| 4d | Frontend: hooks | `src_ui/src/api/hooks.ts` | Edit |
| 5 | Build frontendu → `dist/` | `npm run build` + copy | Build |
| 6 | Dokumentacja | `docs/main-doc.md`, `docs/architecture-report.md`, `README.md` | Edit |
| 7 | known-issues.md | `docs/known-issues.md` | Edit |

---

## Uwagi

1. **`src/__pycache__/`** — zawiera cache zarówno starych (ui, state) jak i nowych plików (main, auth, config). Po usunięciu starych katalogów, pozostałe cache są niegroźne.

2. **stare `logs/cache_results.json`** — może zawierać `needs_review`. Nowy per-survey cache w `logs/survey_cache/` jest niezależny. Stary plik można bezpiecznie usunąć.

3. **Frontend CompletePage** — minimalny ekran, nie ma `st.balloons()` ani fancy animacji. Zgodnie z mapowaniem Streamlit → React z frontend-migration-plan.md: "pomijamy albo lekki odpowiednik".
