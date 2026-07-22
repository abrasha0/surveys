# Etap 6 — Moduł przeglądarki zdjęć

**Zależności:** Etap 3 (endpoint obrazów), Etap 5 (szkielet frontendu).

---

## Cel

Implementacja lewego panelu weryfikacji — przeglądarka zdjęć ankiet z 5
zakładkami stron, tab-switchem ankiet (ready/verified) oraz nawigacją
prev/next. Prawy panel to placeholder gotowy pod formularz dynamiczny (Etap 7).

---

## Co już działa (backend + frontend)

### Backend

| Element | Status |
|---------|--------|
| `GET /api/surveys/{id}/pages/{n}/image` | Zaimplementowane (`src/routers/api.py:69-93`) |
| `GET /api/surveys` | Zaimplementowane (status per ankieta) |
| `GET /api/field-specs` | Zaimplementowane (70 pól) |

### Frontend (Etap 5)

| Element | Status |
|---------|--------|
| Vite + React + Tailwind v4 | Zainstalowane, działa |
| `@tanstack/react-query` | Zainstalowane |
| `zustand` | Zainstalowane (store pusty — do tego etapu) |
| `react-router-dom` | Zainstalowane, routing `/login` → `/app` |
| API client (`apiFetch`) + intercept 401 | Gotowe (`src/api/client.ts`) |
| Hooki (`useSurveys`, `useFieldSpecs`, `surveyImageUrl`) | Gotowe (`src/api/hooks.ts`) |
| Auth + AuthGuard + LoginPage | Gotowe |
| `AppLayout.tsx` | Placeholder "Panel weryfikacji — Etap 6+" → do zastąpienia |

---

## Nowa struktura plików

```
src_ui/src/
├── store/
│   └── verificationStore.ts          # Zustand + localStorage (selectedPage)
├── components/
│   ├── ImageViewer.tsx               # Panel lewy: obraz object-contain + loading/error
│   ├── PageTabs.tsx                  # 5 zakładek "Strona 1"–"Strona 5"
│   └── ui/
│       └── Spinner.tsx               # Loading spinner
├── features/
│   └── verification/
│       ├── VerificationPanel.tsx     # Główny layout: grid 40/60
│       └── SurveyTabs.tsx            # Tab-switch ankiet + Prev/Next
└── app/
    └── AppLayout.tsx                 # Aktualizacja: renderuje <VerificationPanel />
```

---

## Szczegóły implementacji

### Krok 1: `src/store/verificationStore.ts`

Zustand store z minimalnym localStorage sync.

```typescript
interface SurveyUIState {
  selectedPage: number;           // 0-4, pamiętany per ankieta
  showErrors: boolean;            // czy pokazać kropki błędów (Etap 7)
  draftValues: Record<string, unknown>;  // draft pól (Etap 7)
}

interface VerificationStore {
  surveysUI: Record<number, SurveyUIState>;
  getSurveyUI: (surveyId: number) => SurveyUIState;
  setSelectedPage: (surveyId: number, page: number) => void;
  setShowErrors: (surveyId: number, show: boolean) => void;
  updateDraft: (surveyId: number, values: Record<string, unknown>) => void;
  initSurvey: (surveyId: number) => void;
  hydrate: () => void;
}
```

**localStorage:**
- Key: `"ankieter:verification:v1"`
- Zapisuje **tylko** `selectedPage` per `surveyId`
- `showErrors` i `draftValues` tylko w pamięci (session)
- `hydrate()` wywoływane raz w `main.tsx` — odczytuje `selectedPage` z localStorage

**Mapowanie:** UI "Strona 1" → `selectedPage: 0`, "Strona 5" → `selectedPage: 4`

---

### Krok 2: `src/components/ui/Spinner.tsx`

```tsx
export default function Spinner({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-info)]" />
    </div>
  );
}
```

Kolor `--color-info` (niebieski, `#1E88E5`) zgodny z tokenami CSS z Etapu 5.

---

### Krok 3: `src/components/PageTabs.tsx`

**Props:**
```typescript
interface PageTabsProps {
  surveyId: number;
  currentPage: number;           // 0-4
  onChange: (page: number) => void;
}
```

**Render:**
```
[ Strona 1 ] [ Strona 2 ] [ Strona 3 ] [ Strona 4 ] [ Strona 5 ]
```

- 5 przycisków `role="tab"`, kontener `role="tablist"`
- Aktywny: `bg-[var(--color-info)] text-white`
- Nieaktywny: `bg-gray-100 hover:bg-gray-200`
- `onClick` → `store.setSelectedPage(surveyId, page)` + `onChange(page)`
- `aria-selected` dla aktywnego

---

### Krok 4: `src/components/ImageViewer.tsx`

**Props:**
```typescript
interface ImageViewerProps {
  surveyId: number;
  page: number;                  // 0-4
}
```

**Render:**
```tsx
<div className="relative w-full h-full overflow-hidden bg-gray-100">
  {isLoading && <Spinner className="absolute inset-0" />}
  {error && (
    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500 p-4 text-center">
      <p className="font-medium">Brak obrazu dla tej strony</p>
      <p className="text-sm mt-1">{PAGE_DESCRIPTIONS[page] ?? ''}</p>
    </div>
  )}
  <img
    src={surveyImageUrl(surveyId, page)}
    alt={`Strona ${page + 1}`}
    className="w-full h-full object-contain"
    onLoad={() => setLoading(false)}
    onError={() => { setLoading(false); setError(true); }}
  />
</div>
```

- `object-contain` — obraz zawsze w całości, proporcje zachowane, brak scrolla
- `h-full` = 100% wysokości panelu (rodzic `flex-col` + `flex-1`)
- `PAGE_DESCRIPTIONS` z `field_specs.py` (import przez API, hardcoded lub z `useFieldSpecs()`)

---

### Krok 5: `src/features/verification/SurveyTabs.tsx`

**Props:**
```typescript
interface SurveyTabsProps {
  onSurveyChange: (surveyId: number) => void;
}
```

**UI:**
```
┌────────────────────────────────────────────────────────────────────┐
│ [Ankieta 0 ✓] [Ankieta 1 ⟳] [Ankieta 2 ✓] [Ankieta 3 ✗] [Ankieta 4 ⟳] │
│ ◀ Poprzednia ankieta          Następna ankieta ▶                    │
└────────────────────────────────────────────────────────────────────┘
```

**Logika:**
- `useSurveys()` → lista ankiet, polling co 2s
- Filtr: `status === 'ready' || status === 'verified'` — tylko te klikalne
- Zakładki w kolejności `surveyId`
- Status ikony: ✓ (verified), ⟳ (ready), ✗ (error) — error/queued/processing nieklikalne, wyszarzone
- Tooltip: "Ankieta {id} — Gotowa/Zweryfikowana"
- Prev/Next → szukają poprzedniej/następnej w przefiltrowanej liście
- `disabled` na brzegach (pierwszy/ostatni)
- Aktywna zakładka: `border-b-2 border-[var(--color-info)]`
- `onSurveyChange` → `store.initSurveyUI(id)` + callback do `VerificationPanel`

---

### Krok 6: `src/features/verification/VerificationPanel.tsx`

**Layout:**
```tsx
<div className="flex flex-col h-full">
  {/* GÓRA: Tab-switch ankiet + nawigacja */}
  <SurveyTabs onSurveyChange={handleSurveyChange} />

  {/* DÓŁ: Grid 40/60 */}
  <div className="flex-1 flex overflow-hidden">
    {/* LEWY 40%: Obraz + PageTabs */}
    <div className="w-[40%] flex flex-col border-r border-gray-200 bg-white">
      <div className="flex-1 min-h-0">
        <ImageViewer surveyId={currentSurveyId} page={currentPage} />
      </div>
      <PageTabs
        surveyId={currentSurveyId}
        currentPage={currentPage}
        onChange={setCurrentPage}
      />
    </div>

    {/* PRAWY 60%: Placeholder formularza (Etap 7) */}
    <div className="flex-1 flex flex-col overflow-y-auto bg-gray-50 p-4">
      <div className="text-gray-400 text-center py-8">
        Formularz dynamiczny — Etap 7
      </div>
    </div>
  </div>
</div>
```

- `h-full` → wypełnia `<main>` z `AppLayout.tsx` (ma `flex-1 flex overflow-hidden`)
- `overflow-hidden` na kontenerze grid
- Lewy panel `w-[40%]` stały, `flex-col`, `min-h-0` na ImageViewer żeby się skurczył
- Prawy panel `overflow-y-auto` (formularz będzie długi)

---

### Krok 7: `src/app/AppLayout.tsx`

```tsx
// Aktualizacja main:
<main className="flex-1 flex overflow-hidden">
  <VerificationPanel />
</main>
```

Zastąpienie placeholdera "Panel weryfikacji — Etap 6+" komponentem `VerificationPanel`.

---

### Krok 8: `src/app/main.tsx`

```tsx
// Dodaj hydrację store po utworzeniu queryClient:
import { useVerificationStore } from '../store/verificationStore';

// Po stworzeniu queryClient:
useVerificationStore.getState().hydrate();
```

Wywołanie `hydrate()` raz przy starcie — odczytuje `selectedPage` z localStorage.

---

## Kolejność implementacji

| Krok | Plik | Zależności |
|------|------|------------|
| 1 | `src/store/verificationStore.ts` | — |
| 2 | `src/components/ui/Spinner.tsx` | — |
| 3 | `src/components/PageTabs.tsx` | Krok 1 |
| 4 | `src/components/ImageViewer.tsx` | Krok 1, 2 |
| 5 | `src/features/verification/SurveyTabs.tsx` | Krok 1, `useSurveys()` |
| 6 | `src/features/verification/VerificationPanel.tsx` | Kroki 3–5 |
| 7 | `src/app/AppLayout.tsx` | Krok 6 |
| 8 | `src/app/main.tsx` | Krok 1 |

---

## Kryteria akceptacji

1. ✅ **Obraz zawsze w całości widoczny** — `object-contain`, 100% wysokości panelu, brak scrolla
2. ✅ **5 zakładek stron** — "Strona 1"–"Strona 5", płynne przełączanie, stan per ankieta (Zustand)
3. ✅ **Tab-switch ankiet** — górne zakładki z ID + statusem (✓/⟳/✗), tylko `ready`/`verified` klikalne
4. ✅ **Przyciski Prev/Next ankiety** — sensownie umiejscowione, disabled na brzegach
5. ✅ **localStorage persistence** — `selectedPage` przetrwa reload strony (tylko to pole)
6. ✅ **Layout 40/60** — lewy obraz + PageTabs, prawy placeholder formularza
7. ✅ **Error handling** — brak obrazu → komunikat + opis strony
8. ✅ **Docelowa struktura** — zero mocków, gotowe pod DynamicForm (Etap 7)

---

## Kluczowe decyzje implementacyjne

1. **Brak `react-zoom-pan-pinch`** — na start czyste CSS `object-contain`. Dodać później jeśli UX tego wymaga.

2. **Tylko `selectedPage` w localStorage** — `showErrors` i `draftValues` tylko w pamięci. Minimalizm: zero zależności, mało kodu, wystarczające do UX.

3. **Selektor ankiet jako tab-switch** — lepszy UX niż dropdown/radio. Zakładki z ID + ikoną statusu, `ready`/`verified` klikalne, reszta wyszarzona.

4. **Mapowanie 0↔4 ↔ 1↔5** — UI wyświetla "Strona 1"–"Strona 5" (user-friendly), API przyjmuje 0–4. Store trzyma 0–4, PageTabs dodaje +1 do wyświetlenia.

5. **`VerificationPanel` jako osobny komponent** — nie mock w `AppLayout`. Gotowy do rozbudowy o formularz (Etap 7) bez zmian w strukturze.

6. **`PAGE_DESCRIPTIONS` z `field_specs.py`** — error message w `ImageViewer` wyświetla opis strony (np. "Dane demograficzne, praca, styl życia"). Front pobiera z `useFieldSpecs()` i grupuje po `page`.

---

## How to verify

1. **Uruchom backend:** `.venv\Scripts\Activate.ps1; cd src; uvicorn main:app --reload`
2. **Uruchom frontend:** `cd src_ui; npm run dev`
3. **Zaloguj się** → przejdź na `/app`
4. **Widzisz tab-switch ankiet** (gdy są przetworzone) + lewy panel z obrazem + 5 zakładek stron
5. **Kliknij zakładkę strony** → zmienia obraz, wróć → ta sama strona (localStorage)
6. **Przełącz ankiety** → nowy obraz, stan zakładek niezależny per ankieta
7. **Brak obrazu** → komunikat "Brak obrazu dla tej strony"
8. **Reload strony** → wybrana strona przetrwała (localStorage)
9. **Brak błędów TypeScript:** `cd src_ui; npx tsc --noEmit`
10. **Brak błędów lint:** `cd src_ui; npm run lint`
