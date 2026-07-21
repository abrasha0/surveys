# Etap 5 — Szkielet Frontendu (Vite + React + Tailwind)

**Zależności:** Etap 1 (FastAPI backend z auth).

---

## Cel

Inicjalizacja projektu frontendowego w `src_ui/`, uruchomienie go obok backendu
FastAPI (dev proxy), zaimplementowanie ekranu logowania end-to-end oraz
przygotowanie warstwy API client z hookami do dalszych etapów.

---

## Co już działa (backend)

| Element | Status |
|---------|--------|
| `POST /api/auth/login` | Zaimplementowane (cookie) |
| `POST /api/auth/logout` | Zaimplementowane |
| `GET /api/surveys` | Zaimplementowane (status per ankieta) |
| `GET /api/processing/status` | Zaimplementowane (globalny status) |
| `POST /api/processing/start` | Zaimplementowane |
| `POST /api/surveys/{id}/save` | Zaimplementowane |
| `GET /api/surveys/{id}/result` | Zaimplementowane |
| `GET /api/surveys/{id}/pages/{n}/image` | Zaimplementowane |
| `GET /api/field-specs` | **Brakuje — do dodania w ramach tego etapu** |

---

## Nowa struktura plików

```
surveys/
├── src_ui/                          # NOWY katalog frontendu
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts            # Fetch wrapper + intercept 401
│   │   │   └── hooks.ts             # Hooki TanStack Query
│   │   ├── store/
│   │   │   └── (puste — do Etapu 6+)
│   │   ├── features/
│   │   │   └── auth/
│   │   │       └── LoginPage.tsx
│   │   ├── app/
│   │   │   ├── App.tsx              # Root + routing
│   │   │   ├── main.tsx             # Entry point
│   │   │   ├── AuthGuard.tsx        # Guard chroniący trasy
│   │   │   └── AppLayout.tsx        # Placeholder layoutu
│   │   └── index.css                # Tailwind + tokeny CSS
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── eslint.config.js
│   └── package.json
│
├── src/routers/api.py               # MODYFIKACJA — dodanie GET /api/field-specs
```

---

## Krok 1: `src/routers/api.py` — Endpoint `GET /api/field-specs`

**Cel:** Udostępnienie frontendowi definicji 70 pól z `field_specs.py`
 bez duplikowania struktury po stronie Reacta.

### Nowy endpoint (dodaj po istniejących importach)

```python
@router.get("/field-specs")
def get_field_specs():
    return [
        {
            "name": f.name,
            "label": f.label,
            "page": f.page,
            "kind": f.kind,
            "choices": f.choices,
            "min": f.min,
            "max": f.max,
            "csv_header": f.get_csv_header(),
        }
        for f in ALL_FIELDS
    ]
```

### Szczegóły

- Endpoint jest chroniony (ma `dependencies=[Depends(get_current_user)]` na routerze)
- Zwraca tablicę 70 obiektów — jeden na każde pole z `ALL_FIELDS`
- `choices` dla `select` to lista stringów, dla innych typów `null`
- `min`/`max` tylko dla `number` (pole `p2_wiek`: min=18, max=80)
- Brak paginacji — 70 obiektów to małe payload, wystarczy jeden request

### Weryfikacja po implementacji

```bash
curl -b "session_token=<token>" http://localhost:8000/api/field-specs
# Oczekiwane: tablica 70 obiektów z polami name, label, page, kind, choices, ...
```

---

## Krok 2: Inicjalizacja projektu Vite

**Katalog:** `src_ui/` (root projektu)

### 2.1 Scaffold

```bash
npm create vite@latest src_ui -- --template react-ts
cd src_ui
npm install
```

### 2.2 Zależności produkcyjne

```bash
npm install @tanstack/react-query zustand react-router-dom
```

**Dlaczego:**
- `@tanstack/react-query` — cache, polling, mutacje API (F3 z planu frontendowego)
- `zustand` — stan draftu formularza per-ankieta (F10–F13, ale store pusty na razie)
- `react-router-dom` — routing SPA (trasa `/login` vs `/app`)

### 2.3 Zależności dev

```bash
npm install -D tailwindcss @tailwindcss/vite
```

**Tailwind v4** — konfiguracja przez CSS (nie plik `tailwind.config.ts`).
Instalacja `@tailwindcss/vite` jako plugin Vite.

### 2.4 Usunięcie scaffoldu Vite

Po inicjalizacji usuwamy zbędne pliki z `src_ui/src/`:
- `App.css` (nie używamy — mamy Tailwind)
- `assets/` (nie używamy)
- `App.tsx` zastępujemy naszym
- `main.tsx` zastępujemy naszym

---

## Krok 3: `src_ui/vite.config.ts` — Proxy dev

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Kluczowe decyzje:**
- Proxy `/api` → `localhost:8000` — zero problemów CORS w dev
- Frontend dev: `:5173`, backend: `:8000` — dwa osobne procesy
- W produkcji: `npm run build` → `dist/` → FastAPI serwuje na `:8000`

---

## Krok 4: `src_ui/src/api/client.ts` — Fetch wrapper

```typescript
const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (res.status === 401) {
    window.location.href = '/login';
    throw new ApiError(401, 'Not authenticated');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  return res.json();
}
```

### Szczegóły

- `credentials: 'include'` — cookie `session_token` wysyłane z każdym requestem
- Intercept 401 → redirect na `/login` (nie czekamy na React Router — natychmiastowy)
- `ApiError` z `status` — frontend może obsłużyć 400/404/422 osobno
- Brak automatycznego retry — to robi TanStack Query

---

## Krok 5: `src_ui/src/api/hooks.ts` — Hooki TanStack Query

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

// --- Types ---

export interface FieldSpec {
  name: string;
  label: string;
  page: number;
  kind: 'select' | 'text' | 'number';
  choices: string[] | null;
  min: number | null;
  max: number | null;
  csv_header: string;
}

export interface SurveyListItem {
  id: number;
  files: string[];
  status: 'queued' | 'processing' | 'ready' | 'error' | 'verified';
}

export interface ProcessingStatus {
  total: number;
  processed: number;
  errors: number;
  current_survey_id: number | null;
  current_page: number | null;
  current_stage: string | null;
  eta_seconds: number | null;
  is_running: boolean;
}

export interface SurveyResult {
  id: number;
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
}

// --- Hooks ---

export function useFieldSpecs() {
  return useQuery({
    queryKey: ['field-specs'],
    queryFn: () => apiFetch<FieldSpec[]>('/api/field-specs'),
    staleTime: Infinity, // Definicja pól się nie zmienia
  });
}

export function useSurveys() {
  return useQuery({
    queryKey: ['surveys'],
    queryFn: () => apiFetch<SurveyListItem[]>('/api/surveys'),
    refetchInterval: 2000, // Polling co 2s
  });
}

export function useProcessingStatus() {
  return useQuery({
    queryKey: ['processing-status'],
    queryFn: () => apiFetch<ProcessingStatus>('/api/processing/status'),
    refetchInterval: 2000,
  });
}

export function useSurveyResult(surveyId: number | null) {
  return useQuery({
    queryKey: ['survey-result', surveyId],
    queryFn: () => apiFetch<SurveyResult>(`/api/surveys/${surveyId}/result`),
    enabled: surveyId !== null,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (password: string) =>
      apiFetch<{ status: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });
}

export function useStartProcessing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string; total: number }>('/api/processing/start', {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processing-status'] });
    },
  });
}

export function useSaveSurvey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      surveyId,
      values,
      force = false,
    }: {
      surveyId: number;
      values: Record<string, unknown>;
      force?: boolean;
    }) =>
      apiFetch<{ status: string; survey_id: number }>(
        `/api/surveys/${surveyId}/save`,
        {
          method: 'POST',
          body: JSON.stringify({ values, force }),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });
}

export function surveyImageUrl(surveyId: number, page: number): string {
  return `/api/surveys/${surveyId}/pages/${page}/image`;
}
```

### Szczegóły

- `useFieldSpecs()` — `staleTime: Infinity` bo definicja pól się nie zmienia
- `useSurveys()` — polling co 2s (postęp przetwarzania)
- `useProcessingStatus()` — polling co 2s (globalny status + ETA)
- `useSurveyResult()` — `enabled: surveyId !== null` (nie odpala się bez ID)
- `useLogin()` — po sukcesie invaliduje `surveys` (żeby pobrać listę)
- `useSaveSurvey()` — po sukcesie invaliduje `surveys` (status → verified)
- `surveyImageUrl()` — helper do `<img src>`, nie hook (pure function)

---

## Krok 6: `src_ui/src/index.css` — Tailwind + tokeny

```css
@import "tailwindcss";

:root {
  --color-error: #ff4b4b;
  --color-info: #1E88E5;
  --color-success: #4CAF50;
  --color-warning: #FFC107;
}

html, body, #root {
  height: 100vh;
  margin: 0;
  overflow: hidden;
  font-family: system-ui, -apple-system, sans-serif;
}
```

Tokeny kolorów zgodne z `frontend-migration-plan.md` (F2).
`overflow: hidden` na `#root` — brak scrolla okna (SPA 100vh).

---

## Krok 7: `src_ui/src/app/main.tsx` — Entry point

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import '../index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
```

---

## Krok 8: `src_ui/src/app/App.tsx` — Routing

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuthGuard from './AuthGuard';
import AppLayout from './AppLayout';
import LoginPage from '../features/auth/LoginPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/app"
          element={
            <AuthGuard>
              <AppLayout />
            </AuthGuard>
          }
        />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## Krok 9: `src_ui/src/app/AuthGuard.tsx` — Guard

```tsx
import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useSurveys } from '../api/hooks';

export default function AuthGuard({ children }: { children: ReactNode }) {
  const { isLoading, error } = useSurveys();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-info)]" />
      </div>
    );
  }

  if (error) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
```

### Szczegóły

- Próbuje `GET /api/surveys` (chroniony endpoint)
- `isLoading` — spinner podczas ładowania
- `error` (w tym 401 z intercept w `apiFetch`) → redirect na `/login`
- Działa jako sprawniejszy odpowiednik `st.session_state["auth"]`

---

## Krok 10: `src_ui/src/features/auth/LoginPage.tsx` — Ekran logowania

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLogin } from '../../api/hooks';

export default function LoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const login = useLogin();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    login.mutate(password, {
      onSuccess: () => navigate('/app'),
      onError: (err) => {
        if (err instanceof Error) {
          setError(err.message);
        }
      },
    });
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-1">AnkieterAI</h1>
        <p className="text-gray-500 text-center text-sm mb-6">
          System wprowadzania ankiet papierowych
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Hasło
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md
                         focus:outline-none focus:ring-2 focus:ring-[var(--color-info)]
                         focus:border-transparent"
              autoFocus
            />
          </div>

          {error && (
            <div className="text-sm text-[var(--color-error)] bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={login.isPending}
            className="w-full py-2 px-4 bg-[var(--color-info)] text-white
                       rounded-md hover:opacity-90 disabled:opacity-50
                       font-medium transition-opacity"
          >
            {login.isPending ? 'Logowanie...' : 'Zaloguj'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

### Szczegóły

- Tytuł + podtytuł zgodnie z `frontend-migration-plan.md` (F5)
- Błąd logowania inline (odpowiednik `st.error("Nieprawidłowe hasło")`)
- Brak przeładowania strony — `useNavigate` po sukcesie
- `disabled` podczas mutacji — zapobiega podwójnemu kliknięciu
- Kolory z tokenów CSS

---

## Krok 11: `src_ui/src/app/AppLayout.tsx` — Placeholder layoutu

```tsx
import { useNavigate } from 'react-router-dom';

export default function AppLayout() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
    navigate('/login');
  };

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white">
        <span className="font-bold text-lg">AnkieterAI</span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Wyloguj
        </button>
      </header>
      <main className="flex-1 flex items-center justify-center bg-gray-50 text-gray-400">
        Panel weryfikacji — Etap 6+
      </main>
    </div>
  );
}
```

---

## Kolejność implementacji

| Krok | Plik | Zależności | Opis |
|------|------|------------|------|
| 1 | `src/routers/api.py` | brak | Dodanie `GET /api/field-specs` |
| 2 | `src_ui/` (scaffold) | brak | Vite + React + Tailwind + deps |
| 3 | `vite.config.ts` | krok 2 | Proxy `/api` → `:8000` |
| 4 | `src/api/client.ts` | krok 3 | Fetch wrapper + intercept 401 |
| 5 | `src/api/hooks.ts` | krok 4 | Hooki TanStack Query |
| 6 | `src/index.css` | krok 2 | Tailwind + tokeny CSS |
| 7 | `src/app/main.tsx` | kroki 2, 6 | Entry point + QueryClient |
| 8 | `src/app/App.tsx` | krok 7 | Routing (`/login`, `/app`) |
| 9 | `src/app/AuthGuard.tsx` | krok 5 | Guard (próba requestu → 401 → login) |
| 10 | `src/features/auth/LoginPage.tsx` | kroki 5, 8 | Formularz logowania |
| 11 | `src/app/AppLayout.tsx` | krok 8 | Placeholder layoutu + logout |

---

## Kryteria akceptacji

1. `cd src_ui && npm run dev` startuje na `:5173`
2. `cd src && uvicorn main:app --reload` startuje na `:8000`
3. Otwarcie `:5173` → redirect na `/login`
4. Logowanie hasłem `a` → przejście na `/app` → placeholder "Panel weryfikacji"
5. `GET /api/field-specs` zwraca 70 pól (weryfikacja z `curl`)
6. Brak błędów TypeScript (`npx tsc --noEmit`)
7. Brak błędów ESLint (`npm run lint`)
8. `npm run build` buduje `dist/` bez błędów
9. Wylogowanie → powrót na `/login`

## How to verify

1. **Uruchom backend:** `.venv\Scripts\Activate.ps1; cd src; uvicorn main:app --reload`
2. **Uruchom frontend:** `cd src_ui; npm run dev`
3. **Sprawdź proxy:** Otwórz `:5173` → powinien redirectować na `/login`
4. **Zaloguj się:** Wpisz hasło `a` → powinien przejść na `/app`
5. **Sprawdź field-specs:** `curl -b "session_token=<token>" http://localhost:8000/api/field-specs`
6. **Sprawdź build:** `cd src_ui; npm run build` → katalog `dist/` z plikami

---

## Kluczowe decyzje implementacyjne

1. **Tailwind v4 zamiast v3** — nowszy, konfiguracja przez CSS (nie plik),
   lepsza wydajność builda. `@tailwindcss/vite` jako plugin Vite.

2. **`zustand` zainstalowany, ale store pusty** — skoro robimy pełny scaffold,
   dodajemy od razu zależność. Store na draft formularza powstanie w Etapie 6+.
   Nie instalujemy go osobno przy okazji następnego etapu.

3. **`react-router-dom` zamiast `wouter`** — `wouter` jest lżejszy, ale
   `react-router-dom` ma większe community i lepsze typowanie. Dla małej apki
   różnica jest nieistotna, a React Router jest standardem.

4. **`useSurveys()` jako AuthGuard** — zamiast osobnego hooka `useAuth()`,
   próbujemy pobrać listę ankiet (chroniony endpoint). Jeśli 401 → login.
   Zero redundancji — hook jest potrzebny niezależnie.

5. **`staleTime: Infinity` dla `useFieldSpecs()`** — definicja 70 pól
   nigdy się nie zmienia w trakcie sesji. Cache'owanie bez limitu.
   Refetch tylko przy manualnym invalidacji.

6. **Brak `react-hook-form`** — formularz będzie w pełni kontrolowany
   (controlled inputs). Walidacja "czy pole puste" jest prosta i nie
   potrzebuje biblioteki. Zustand trzyma draft per-ankieta.
