# Etap 7 — Moduł Formularza Dynamicznego

**Zależności:** Etap 2 (field specs dostępne przez API), Etap 5 (szkielet frontendu), Etap 6 (moduł przeglądarki zdjęć).

---

## Cel

Zastąpienie placeholdera w prawym panelu weryfikacji w pełni funkcjonalnym formularzem generowanym dynamicznie z `field_specs` (70 pól, 5 stron), z prefillem z AI, walidacją, skrótem Spacja = "Zatwierdź i następna", oraz jasną nawigacją.

---

## Co Już Działa (Backend + Frontend po Etapie 6)

### Backend

| Element | Status |
|---------|--------|
| `GET /api/field-specs` | 70 pól (name, label, page, kind, choices, min, max, csv_header) |
| `GET /api/surveys` | Lista ankiet ze statusem per ankieta |
| `GET /api/surveys/{id}/pages/{page}/image` | Serwowanie obrazów |
| `GET /api/surveys/{id}/result` | Wynik AI dla ankiety `ready`/`error` |
| `POST /api/surveys/{id}/save` | Walidacja + zapis do CSV + status → `verified` |

### Frontend (Etap 6)

| Element | Status |
|---------|--------|
| `useVerificationStore` (Zustand) | `selectedPage`, `showErrors`, `draftValues` per ankieta |
| `ImageViewer`, `PageTabs`, `SurveyTabs`, `VerificationPanel` | Gotowe |
| Hooki API | `useFieldSpecs`, `useSurveys`, `useSurveyResult`, `useSaveSurvey` |
| Layout | 40/60 (lewy obraz, prawy placeholder) |

---

## Decyzje Ustalone Przy Iteracji Planu

| # | Temat | Decyzja |
|---|-------|---------|
| 1 | Textarea dla pól `kind: "text"` | ✅ Tak — `<textarea rows={3}>` dla wszystkich pól tekstowych |
| 2 | Debounce draft save | ✅ 500ms |
| 3 | Przycisk "Zatwierdź mimo błędów" (force) | ❌ Usunięty — brak w UI, backend parameter nieużywany na razie |
| 4 | Weryfikacja formatu CSV | ✅ OK na razie — dopasowanie do konkretnego pliku referencyjnego w przyszłości |

---

## Nowa Struktura Plików

```
src_ui/src/
├── hooks/
│   └── useSpaceShortcut.ts              # Globalny skrót Spacja
├── store/
│   └── verificationStore.ts             # Rozszerzenie: hydrateDrafts, saveDraft, clearDraft
├── features/
│   └── verification/
│       ├── DynamicForm.tsx              # Główny formularz dynamiczny
│       ├── FieldRenderer.tsx            # Pojedyncze pole (select/number/textarea)
│       ├── SurveyHeader.tsx             # Header + tab-switch + 3 przyciski nawigacji
│       └── VerificationPanel.tsx        # Integracja DynamicForm (aktualizacja)
└── app/
    └── main.tsx                         # Wywołanie hydrateDrafts()
```

---

## Szczegóły Implementacji

### Krok 1: `src_ui/src/store/verificationStore.ts` — Rozszerzenie Stanu

**Dodane pola w `SurveyUIState`:**
```typescript
interface SurveyUIState {
  selectedPage: number;
  showErrors: boolean;
  draftValues: Record<string, unknown>;
  lastSaved: number;           // timestamp ostatniego zapisu (debounce)
}
```

**Dodane metody w `VerificationStore`:**
```typescript
saveDraft: (surveyId: number) => void;           // debounced 500ms, localStorage
clearDraft: (surveyId: number) => void;          // po udanym zapisie (verified)
hydrateDrafts: () => void;                       // wywoływane w main.tsx
```

**localStorage — nowy klucz:**
- Key: `"ankieter:drafts:v1"`
- Struktura: `{ "0": { "p1_plec": "Kobieta", ... }, "1": { ... } }`
- Zapisywane tylko `draftValues` per `surveyId` (string keys)
- `selectedPage` pozostaje w `"ankieter:verification:v1"` (istniejące)

**Debounce:** 500ms — użyj `setTimeout`/`clearTimeout` w `saveDraft`, timer per `surveyId`.

---

### Krok 2: `src_ui/src/hooks/useSpaceShortcut.ts` — Hook Skrótu

```typescript
export function useSpaceShortcut(enabled: boolean, onSpace: () => void) {
  useEffect(() => {
    if (!enabled) return;
    const handler = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        const isInput = target.tagName === 'INPUT' 
                     || target.tagName === 'TEXTAREA' 
                     || target.tagName === 'SELECT' 
                     || target.isContentEditable;
        if (!isInput) {
          e.preventDefault();
          onSpace();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [enabled, onSpace]);
}
```

---

### Krok 3: `src_ui/src/features/verification/FieldRenderer.tsx` — Pojedyncze Pole

**Props:**
```typescript
interface FieldRendererProps {
  field: FieldSpec;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  error?: string;
  showErrors: boolean;
}
```

**Renderowanie wg `field.kind`:**
- `select` → `<select>` z `<option value="">Wybierz...</option>` + `field.choices?.map(c => <option key={c}>{c}</option>)`
- `number` → `<input type="number" min={field.min} max={field.max} step={1}>`
- `text` → `<textarea rows={3}>` (wszystkie pola tekstowe)

**Label:** `field.label` (zawiera numer, np. "1. Płeć")

**Error:** jeśli `showErrors && error` → `<p className="text-red-600 text-sm mt-1">{error}</p>`

**Style:** Tailwind `w-full`, `border`, `rounded`, `px-3 py-2`, `focus:ring-2 focus:ring-[var(--color-info)]`

---

### Krok 4: `src_ui/src/features/verification/DynamicForm.tsx` — Rdzeń Formularza

**Props:**
```typescript
interface DynamicFormProps {
  surveyId: number;
  fieldSpecs: FieldSpec[];
  aiResult: Record<string, unknown> | null;
  onSave: (values: Record<string, unknown>) => Promise<void>;
  onNextSurvey: () => void;
  disabled?: boolean;
}
```

**Stan wewnętrzny:**
- `currentPage` — z `useVerificationStore` (selectedPage)
- `showErrors` — z store
- `errors: Record<string, string>` — walidacja lokalna

**Logika:**
1. **Grupowanie pól:** `fieldSpecs.filter(f => f.page === currentPage)`
2. **Prefill wartości:** `draftValues[field.name] ?? aiResult?.[field.name] ?? ""`
3. **onChange:** `store.updateDraft(surveyId, { [field.name]: value })` + `store.saveDraft(surveyId)` (debounced)
4. **Walidacja onBlur/onChange:**
   - `select`: wartość w `choices` (case-insensitive)
   - `number`: parsowanie do int, sprawdzenie `min`/`max`
   - `text`: `trim()`
5. **handleSave:** pobiera `draftValues` ze store, wywołuje `onSave(values)`, na sukces → `store.clearDraft(surveyId)` + `onNextSurvey()`
6. **Spacja:** `useSpaceShortcut(!disabled, handleSave)`
7. **Przyciski na dole formularza:**
   - "◀ Poprzednia strona" (disabled na stronie 0)
   - "Następna strona ▶" (disabled na stronie 4)
   - "Zatwierdź ankietę" (type="submit", variant="primary")

---

### Krok 5: `src_ui/src/features/verification/SurveyHeader.tsx` — Nowa Nawigacja (Issue #3, #4)

**Props:**
```typescript
interface SurveyHeaderProps {
  currentSurveyId: number | null;
  clickableSurveys: SurveyListItem[];  // status ready/verified
  currentIndex: number;
  onPrev: () => void;
  onNext: () => void;
  onSave: () => void;
  onSurveyChange: (surveyId: number) => void;
}
```

**Render:**
```tsx
<div className="flex items-center justify-between px-2 py-2 border-b border-gray-200 bg-white">
  {/* Lewo: licznik */}
  <span className="font-medium text-sm">
    Ankieta {currentIndex + 1} z {clickableSurveys.length}
  </span>

  {/* Środek: tab-switch ankiet (scrollable) */}
  <div className="flex-1 flex overflow-x-auto mx-4">
    {clickableSurveys.map(survey => (
      <button
        key={survey.id}
        role="tab"
        aria-selected={survey.id === currentSurveyId}
        disabled={false} // wszystkie clickable
        onClick={() => onSurveyChange(survey.id)}
        className={...} // styl aktywnego/nieaktywnego z ikoną statusu
      >
        <span>{survey.id}</span>
        <span className="text-xs">{statusIcon(survey.status)}</span>
      </button>
    ))}
  </div>

  {/* Prawo: 3 przyciski nawigacji w jednym rzędzie */}
  <div className="flex items-center gap-2">
    <Button onClick={onPrev} disabled={currentIndex === 0} variant="secondary">
      Poprzednia ankieta
    </Button>
    <Button onClick={onSave} variant="primary">
      Zatwierdź ankietę
    </Button>
    <Button onClick={onNext} disabled={currentIndex === clickableSurveys.length - 1} variant="secondary">
      Następna ankieta
    </Button>
  </div>
</div>
```

**Ikony statusu:**
- `verified` → ✓
- `ready` → ⟳
- `error` → ✗ (nieklikalne, opacity-40)

---

### Krok 6: `src_ui/src/features/verification/VerificationPanel.tsx` — Integracja

**Zmiany:**
1. Import `DynamicForm`, `SurveyHeader`, `useFieldSpecs`, `useSurveyResult`, `useSaveSurvey`
2. Stan `isSaving` (z mutation `useSaveSurvey`)
3. `fieldSpecs` z `useFieldSpecs()` (cached, `staleTime: Infinity`)
4. `surveyResult` z `useSurveyResult(currentSurveyId)`
5. `clickableSurveys` z `useSurveys()` (filtrowane `ready`/`verified`)
6. `currentIndex` = `clickableSurveys.findIndex(s => s.id === currentSurveyId)`
7. Handler `handleSave` → `saveSurveyMutation.mutateAsync({ surveyId: currentSurveyId, values, force: false })`
8. `handleNextSurvey` → znajdź następną w `clickableSurveys`, `initSurvey`, `setCurrentSurveyId`
9. Render:
   ```tsx
   <div className="flex flex-col h-full">
     <SurveyHeader
       currentSurveyId={currentSurveyId}
       clickableSurveys={clickableSurveys}
       currentIndex={currentIndex}
       onPrev={handlePrevSurvey}
       onNext={handleNextSurvey}
       onSave={handleSave}
       onSurveyChange={handleSurveyChange}
     />
     <div className="flex-1 flex overflow-hidden">
       {/* Lewy panel - bez zmian */}
       <div className="w-[40%] flex flex-col border-r border-gray-200 bg-white">
         <div className="flex-1 min-h-0">
           <ImageViewer surveyId={currentSurveyId} page={currentPage} />
         </div>
         <PageTabs ... />
       </div>
       {/* Prawy panel - DynamicForm */}
       <div className="flex-1 flex flex-col overflow-y-auto bg-gray-50 p-4">
         {currentSurveyId !== null && (
           <DynamicForm
             surveyId={currentSurveyId}
             fieldSpecs={fieldSpecs.data ?? []}
             aiResult={surveyResult.data?.result ?? null}
             onSave={handleSave}
             onNextSurvey={handleNextSurvey}
             disabled={isSaving}
           />
         )}
       </div>
     </div>
   </div>
   ```

---

### Krok 7: `src_ui/src/app/main.tsx` — Hydracja Draftów

```tsx
import { useVerificationStore } from '../store/verificationStore';

// ...

useVerificationStore.getState().hydrate();
useVerificationStore.getState().hydrateDrafts();  // NOWE
```

---

## Kolejność Implementacji

| Krok | Plik | Zależności |
|------|------|------------|
| 1 | `verificationStore.ts` (rozszerzenie) | — |
| 2 | `useSpaceShortcut.ts` | — |
| 3 | `FieldRenderer.tsx` | Krok 1 (typy store) |
| 4 | `DynamicForm.tsx` | Kroki 1–3, hooki API |
| 5 | `SurveyHeader.tsx` | — |
| 6 | `VerificationPanel.tsx` (integracja) | Kroki 4–5 |
| 7 | `main.tsx` (hydrateDrafts) | Krok 1 |
| 8 | `tsc --noEmit`, `npm run lint`, `npm run build` | Wszystkie |

---

## Kryteria Akceptacji

1. ✅ Formularz renderuje **70 pól** z `fieldSpecs`, pogrupowanych po 5 stronach (zakładki `PageTabs` przełączają widoczne pola)
2. ✅ **Prefill z AI** — pola wypełnione wartościami z `useSurveyResult`, edytowalne
3. ✅ **Walidacja typów** — select sprawdza choices, number sprawdza min/max, text trim (textarea rows=3)
4. ✅ **Draft persistence** — przeskakowanie stron/ankiet nie traci wpisywanych danych (Zustand + localStorage, debounce 500ms)
5. ✅ **Spacja = "Zatwierdź ankietę i następna"** — globalny shortcut, działa gdy focus nie w inpucie/textarea/select
6. ✅ **Nawigacja jasna** — header "Ankieta X z Y", przyciski "Poprzednia ankieta", "Zatwierdź ankietę", "Następna ankieta" w jednym rzędzie (issue #3, #4)
7. ✅ **Zapis do CSV** — `POST /save` zwraca 200, status ankiety → `verified`, następna `ready`/`verified` ładuje się automatycznie
8. ✅ **Brak błędów** TS/Lint/Build
9. ✅ **CSV** — zgodność z `ALL_FIELDS` (weryfikacja później z plikiem referencyjnym)

---

## Pliki Do Stworzenia (4 nowe)

1. `src_ui/src/features/verification/DynamicForm.tsx`
2. `src_ui/src/features/verification/FieldRenderer.tsx`
3. `src_ui/src/hooks/useSpaceShortcut.ts`
4. `src_ui/src/features/verification/SurveyHeader.tsx`

## Pliki Do Edycji (4)

1. `src_ui/src/store/verificationStore.ts`
2. `src_ui/src/features/verification/VerificationPanel.tsx`
3. `src_ui/src/features/verification/SurveyTabs.tsx` → **zastąpione przez** `SurveyHeader.tsx`
4. `src_ui/src/app/main.tsx`

---

## Uwagi Implementacyjne

- **Brak `force` save** — przycisk "Zatwierdź mimo błędów" nie jest implementowany. Walidacja błędów blokuje zapis (mutation nie wywoływana). Backend parameter `force` pozostaje dostępny na przyszłość.
- **CSV walidacja** — na tym etapie zakładamy zgodność z `ALL_FIELDS`. Dopasowanie do konkretnego pliku referencyjnego w osobnym kroku.
- **Textarea dla wszystkich `text`** — uproszczenie, spójne UX. Można dopracować w przyszłości (np. `rows` zależne od pola).
- **Debounce per surveyId** — timer przechowywany w store (np. `draftTimers: Record<number, NodeJS.Timeout>`).