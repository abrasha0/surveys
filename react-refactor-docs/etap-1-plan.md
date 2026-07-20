# Etap 1 — Szkielet backendu FastAPI

## Cel

Stworzenie minimalnego szkieletu backendu FastAPI, który:
- Startuje na porcie 8000
- Serwuje placeholderowy frontend (dist/)
- Wystawia API z auth, listą ankiet i serwowaniem obrazów
- Przygotowuje grunt pod kolejne etapy (processing worker, save endpoint)

---

## Struktura nowych plików

```
surveys/
├── src/
│   ├── main.py                    # NOWY: punkt wejścia FastAPI
│   ├── auth.py                    # NOWY: token + dependency
│   ├── routers/
│   │   ├── __init__.py
│   │   └── api.py                 # NOWY: router /api/*
│   ├── config.py                  # ISTNIEJĄCY (bez zmian)
│   ├── logger.py                  # ISTNIEJĄCY (bez zmian)
│   ├── domain/                    # ISTNIEJĄCY (bez zmian)
│   ├── ai/                        # ISTNIEJĄCY (bez zmian)
│   └── ingestion/                 # ISTNIEJĄCY (bez zmian)
├── dist/
│   └── index.html                 # NOWY: minimalny placeholder
├── requirements.txt               # ZAKTUALIZOWANY
└── config.yaml.example            # ZAKTUALIZOWANY (dodane surveys_dir)
```

---

## Kolejność implementacji

| # | Plik | Zależności | Weryfikacja |
|---|------|-----------|-------------|
| 1 | `requirements.txt` | — | `pip install -r requirements.txt` |
| 2 | `src/auth.py` | `config.py` | Import bez błędów |
| 3 | `src/routers/__init__.py` | — | Pusty plik |
| 4 | `src/routers/api.py` | `auth.py`, `file_grouping.py`, `config.py` | Import bez błędów |
| 5 | `src/main.py` | `routers/api.py`, `logger.py` | `uvicorn src.main:app` startuje |
| 6 | `dist/index.html` | — | `GET /` zwraca HTML |
| 7 | `config.yaml.example` | — | Dodany `surveys_dir` |

---

## Szczegóły implementacji

### Krok 1: `requirements.txt`

Dodaj:
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
```

Zachowaj wszystkie istniejące zależności.

---

### Krok 2: `src/auth.py`

Moduł uwierzytelniania. Hasło z config (hardcoded) — proste podejście.

**Elementy:**
- `_SECRET_KEY`: `secrets.token_hex(32)` generowany przy starcie
- `create_session_token(password)` → `str | None`: porównuje z `config.app["password"]`, zwraca token lub `None`
- `verify_session_token(token)` → `bool`: weryfikuje token
- `get_current_user(token: str = Cookie("session_token"))` → FastAPI `Depends()` — zwraca usera lub `HTTPException(401)`

**Endpointy (osobny router auth — nie jest chroniony):**

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/auth/login` | POST | `{"password": "..."}` | `200 {"status": "ok"}` + Set-Cookie |
| `/api/auth/logout` | POST | — | `200` + kasuje cookie |

---

### Krok 3: `src/routers/__init__.py`

Pusty plik.

---

### Krok 4: `src/routers/api.py`

```python
router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
```

**Endpointy (z auth dependency na routerze):**

| Endpoint | Status w Etapie 1 | Opis |
|----------|-------------------|------|
| `GET /api/health` | ✅ 200 OK | Publiczny (bez auth) — `{"status": "ok"}` |
| `GET /api/surveys` | ✅ 200 + lista | Skanowanie katalogu, grupowanie po 5 |
| `GET /api/surveys/{id}/pages/{n}/image` | ✅ 200 image/jpeg | Serwowanie obrazu binarnego |
| `POST /api/processing/start` | 🔲 501 Stub | Endpoint z Etapu 3 |
| `GET /api/processing/status` | 🔲 501 Stub | Endpoint z Etapu 3 |
| `POST /api/surveys/{id}/save` | 🔲 501 Stub | Endpoint z Etapu 4 |

**`GET /api/surveys` — logika:**
1. Odczytaj ścieżkę katalogu z `config.app["surveys_dir"]`
2. `Path(surveys_dir).glob("*")` → posortuj → grupuj po 5 (file_grouping.py)
3. Zwraca: `[{"id": 0, "files": ["1.jpg", "2.jpg", ...], "status": "queued"}]`

**`GET /api/surveys/{id}/pages/{n}/image` — logika:**
1. Pobierz grupę o `id`
2. Zwróć plik `files[n]` jako `FileResponse(media_type="image/jpeg")`
3. Walidacja: 0 <= n < 5

---

### Krok 5: `src/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from logger import setup_logging
from routers.api import router as api_router, auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(...)
    yield

app = FastAPI(title="AnkieterAI", lifespan=lifespan)

# Auth router (bez globalnego auth dependency)
app.include_router(auth_router)

# API router (z globalnym auth dependency)
app.include_router(api_router)

# Static files — placeholder
dist_path = Path(__file__).parent.parent / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
```

**Uruchomienie:** `uvicorn src.main:app --reload --port 8000` z roota projektu

---

### Krok 6: `dist/index.html`

Minimalny placeholder:
```html
<!DOCTYPE html>
<html>
<head><title>AnkieterAI</title></head>
<body>
  <h1>AnkieterAI</h1>
  <p>Frontend wkrótce. Backend API: <a href="/api/health">/api/health</a></p>
</body>
</html>
```

---

### Krok 7: `config.yaml.example`

Dodaj w sekcji `app`:
```yaml
app:
  surveys_dir: "surveys_data"  # Katalog ze zdjęciami ankiet
```

---

## Kryteria akceptacji

- [ ] `uvicorn src.main:app --reload --port 8000` startuje
- [ ] `GET /api/health` → `200 {"status": "ok"}`
- [ ] `GET /api/surveys` (bez cookie) → `401`
- [ ] `POST /api/auth/login` z poprawnym hasłem → `200` + cookie w response
- [ ] `GET /api/surveys` (z cookie) → `200 [{"id":0, "files":[...]}]`
- [ ] `GET /api/surveys/0/pages/0/image` → `200 image/jpeg`
- [ ] `GET /` → `200` placeholder HTML
- [ ] `config.py` i `logger.py` działają bez zmian

---

## Decyzje projektowe

| Pytanie | Decyzja | Uzasadnienie |
|---------|---------|-------------|
| Lokalizacja main.py | `src/main.py` | Importy `config`, `domain`, `ai` działają naturalnie bez `sys.path` |
| Algorytm tokenu | hmacSHA256(password + random_secret) | Proste, wystarczające dla single-user app, hasło hardcoded |
| Placeholder dist/ | Minimalny index.html | Wystarczający do testów, frontend powstanie w Etapie 5 |
| Auth scope | Cookie-based, bez expiry | Zgodnie z Etap 0 decyzja #1 — zero security poza "nie wchodzisz bez hasła" |
| Surveys dir | Nowy klucz w config.app | Umożliwia konfigurację ścieżki do katalogu ze zdjęciami |

---

## Uwagi

1. **Surveys dir** — katalog ze zdjęciami musi istnieć przed uruchomieniem. W Etapie 3 worker będzie skanował ten katalog.
2. **StaticFiles** — `html=True` wymaga `dist/index.html`. Gdy katalog nie istnieje, appka startuje bez mountu (OK).
3. **Stub endpointy** — processing/start, processing/status, save zwracają 501 w Etapie 1, będą zaimplementowane w Etapach 3-4.
