# AnkieterAI — Frontend (React + Vite + TypeScript)

Frontend dla systemu AnkieterAI — automatycznego wprowadzania ankiet papierowych do formy cyfrowej.

## Stack

- React 19, TypeScript 6, Vite 8
- React Router DOM 7 (routing SPA)
- TanStack React Query 5 (cache serwerowy, polling co 2s)
- Zustand 5 (stan lokalny UI, localStorage persistence)
- Tailwind CSS 4 (stylowanie utility-first)
- Oxlint (linter)

## Struktura katalogów

```
src/
├── app/                      # Routing, layout, guard autoryzacji
│   ├── main.tsx              # Entry point, inicjalizacja QueryClient + hydracja Zustand
│   ├── App.tsx               # Definicja ścieżek (/, /login, /app, /complete)
│   ├── AppLayout.tsx         # Shell aplikacji (header + progress bar + panel weryfikacji)
│   └── AuthGuard.tsx         # Guard sprawdzający sesję (próba requestu -> 401 -> redirect /login)
├── api/
│   ├── client.ts             # Fetch wrapper (credentials: include, intercept 401)
│   └── hooks.ts              # TanStack Query hooks (useSurveys, useProcessingStatus, itd.)
├── features/
│   ├── auth/
│   │   └── LoginPage.tsx     # Ekran logowania (hasło)
│   ├── verification/         # Panel weryfikacji (główny widok aplikacji)
│   │   ├── VerificationPanel.tsx       # Orchestrator: lista ankiet -> wybór -> widok side-by-side
│   │   ├── DynamicForm.tsx             # Formularz z walidacją, draft persistence, skrót Spacja
│   │   ├── FieldRenderer.tsx           # Renderer pojedynczego pola (select/number/textarea)
│   │   ├── SurveyHeader.tsx            # Nawigacja między ankietami (Prev/Next + zakładki)
│   │   └── ProcessingProgressBar.tsx   # Pasek postępu przetwarzania (ETA, etap modelu, błędy)
│   └── complete/
│       └── CompletePage.tsx            # Ekran zakończenia (CSV download, nowa sesja)
├── store/
│   └── verificationStore.ts  # Zustand store (UI state: selectedPage, showErrors, draftValues + localStorage)
├── hooks/
│   └── useSpaceShortcut.ts   # Globalny skrót klawiszowy Spacja (ignorowany przy focusie w inputach)
└── components/
    ├── ImageViewer.tsx       # Podgląd obrazu ankiety (object-contain, 100% height)
    ├── PageTabs.tsx          # Zakładki stron (1-5), wybór pamiętany per ankieta
    └── ui/
        └── Spinner.tsx       # Wskaźnik ładowania
```

## Rozwój

```powershell
npm run dev       # Dev server na :5173 z proxy /api -> localhost:8000
npm run build     # Budowa do dist/
npm run lint      # Linting (Oxlint)
```

## API

Frontend komunikuje się z backendem FastAPI przez REST API na porcie 8000.
W developmencie Vite proxy przekierowuje `/api` -> `localhost:8000`.

Wszystkie endpointy API (prefix `/api`) są chronione przez HMAC cookie `session_token`.
Wyjątek: `GET /api/auth/health` (publiczny).
