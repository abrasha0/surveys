# Etap 8 — Topbar/nawigacja + integracja postępu i ETA

**Zależności:** Etapy 3, 6, 7.

---

## Cel

Dodanie globalnego paska postępu batcha z ETA i wzmocnienie wizualnego rozróżnienia ankiet w pasku nawigacyjnym, tak aby użytkownik widział łączny postęp przetwarzania i mógł zacząć weryfikację pierwszych gotowych ankiet, zanim reszta batcha się doprocesuje.

---

## Co Już Działa (Po Etapie 7)

### Backend

| Element | Status |
|---------|--------|
| `GET /api/processing/status` | Zwraca `total`, `processed`, `errors`, `current_survey_id`, `current_page`, `current_stage` (vlm/format), `eta_seconds`, `is_running` |
| `POST /api/processing/start` | Uruchamia globalnego workera |
| `POST /api/processing/stop` | Zatrzymuje workera |

### Frontend (Etap 7)

| Element | Status |
|---------|--------|
| `useProcessingStatus` (hook) | Polling `/api/processing/status` co 2s |
| `SurveyHeader` | Nawigacja: "Ankieta X z Y", statusy zakładek (✓ / ⟳ / ✗), przyciski "Poprzednia ankieta", "Zatwierdź ankietę", "Następna ankieta" |
| `DynamicForm`, `FieldRenderer`, `VerificationPanel` | Działający formularz z walidacją i draft persistence |
| `AppLayout` | Header + VerificationPanel, brak paska postępu |

---

## Czego Brakuje

| # | Element | Status |
|---|---------|--------|
| 1 | Globalny pasek postępu z ETA podpięty pod `/api/processing/status` | ❌ |
| 2 | Lepsze wizualne rozróżnienie ankiet `ready` vs `queued`/`processing`/`error` w `SurveyHeader` | ❌ (częściowo — ikony są, ale różnicowanie słabe) |
| 3 | Przycisk "Rozpocznij analizę" (gdy worker nieaktywny i są nieprzetworzone ankiety) | ❌ (opcjonalny) |

---

## Plan Implementacji

### Krok 1: `src_ui/src/features/verification/ProcessingProgressBar.tsx` — NOWY

Komponent renderujący globalny pasek postępu.

**Props:**
```typescript
interface ProcessingProgressBarProps {
  status: ProcessingStatus | undefined;
  isLoading: boolean;
  onStart?: () => void;
  isStarting?: boolean;
}
```

**Renderowanie:**
- Wizualny pasek postępu (wypełnienie: `processed / total`, kolory: zielony = gotowe, czerwony = błędy, niebieski = w trakcie)
- Tekst: `Przetworzono: X z Y · Błędy: Z · ETA: ~MM:SS` (lub `Obliczanie...` gdy brak ETA)
- Aktualna aktywność: `VLM — strona 3/5, ankieta 2` (z `current_stage`, `current_page`, `current_survey_id`)
- Gdy `is_running === false` i są nieprzetworzone: przycisk "Rozpocznij analizę"
- Gdy `is_running === true`: etykieta "Przetwarzanie w tle..."
- Gdy wszystkie przetworzone: etykieta "Wszystkie ankiety przetworzone ✓"

**Style:** Tailwind, fixed height ~48px, border-bottom, wyszarzone tło (`bg-gray-100`).

### Krok 2: `src_ui/src/app/AppLayout.tsx` — EDYCJA

- Import `useProcessingStatus`, `useStartProcessing` z hooks
- Import `ProcessingProgressBar`
- Dodanie stanu dla `ProcessingProgressBar` między headerem a `<main>`

### Krok 3: `src_ui/src/features/verification/SurveyHeader.tsx` — EDYCJA

Aktualizacja wizualnego rozróżnienia zakładek ankiet:

| Status | Styl | Ikona | Clickable |
|--------|------|-------|-----------|
| `ready` | Zielone tło, biały tekst | ⟳ | ✅ Tak |
| `verified` | Zielone tło, biały tekst | ✓ | ✅ Tak |
| `processing` | Niebieskie tło, biały tekst, animacja pulsu | ⏳ | ❌ Nie |
| `queued` | Szare tło, szary tekst | ⏸ | ❌ Nie |
| `error` | Czerwone tło, biały tekst | ✗ | ❌ Nie |

Tooltip (`title` attr) dla nieklikalnych: "W trakcie przetwarzania...", "W kolejce", "Błąd przetwarzania".

### Krok 4: Weryfikacja

```bash
cd src_ui
npm run lint
npx tsc --noEmit
npm run build
```

---

## Podsumowanie Zmian w Plikach

| Plik | Akcja | Opis |
|------|-------|------|
| `src_ui/src/features/verification/ProcessingProgressBar.tsx` | **NOWY** | Globalny pasek postępu z ETA |
| `src_ui/src/app/AppLayout.tsx` | **EDYCJA** | Integracja paska postępu |
| `src_ui/src/features/verification/SurveyHeader.tsx` | **EDYCJA** | Lepsze wizualne różnicowanie statusów |

---

## Kryteria Akceptacji

1. Globalny pasek postępu widoczny w layoutcie, pokazuje `processed/total`, liczbę błędów, aktualny etap modelu (VLM/formatter) i ETA
2. Użytkownik może kliknąć dowolną ankietę `ready`/`verified` i zacząć weryfikację, zanim worker skończy resztę batcha (interleaved verification — działa od Etapu 3, teraz tylko wizualne wzmocnienie)
3. Ankiety `queued`/`processing`/`error` są wizualnie odróżnialne od `ready` (kolor, ikona, tooltip)
4. Przycisk "Rozpocznij analizę" pojawia się gdy worker nieaktywny i są nieprzetworzone ankiety
5. Brak błędów TS/Lint/Build
