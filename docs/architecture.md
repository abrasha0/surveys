# Architecture

AnkieterAI is a FastAPI backend with a background worker that calls local Ollama
models, and a React single-page app for verification. Everything runs on one machine;
survey images are read from a local directory, not uploaded.

```
┌──────────────────┐  REST /api   ┌──────────────────┐        ┌──────────────────┐
│ React SPA        │─────────────▶│ FastAPI          │───────▶│ ProcessingWorker │
│ src/frontend     │◀─────────────│ src/backend      │        │ (asyncio task)   │
└──────────────────┘   polling    └────────┬─────────┘        └────────┬─────────┘
                                           │                           │ /api/chat
                                           ▼                           ▼
                                  working_vault/               Ollama: VLM + text model
                                  processed.json, drafts,
                                  CSV, logs, dist/
```

In production (`run_prod.ps1` / `run_prod.sh`) FastAPI also serves the built frontend from
`working_vault/dist` (or `src/frontend/dist`) and falls back to `index.html` for client
routes. In development (`run_dev.ps1` / `run_dev.sh`) the Vite dev server on port 5173 serves the
frontend and proxies `/api` to port 8000. Without a frontend build, `/` shows a short
page with setup instructions.

## Backend (`src/backend`)

| Module | Responsibility |
|---|---|
| `main.py` | App entry point: logging setup, password check on startup, routers, static files |
| `config.py` | Loads `config.yaml` (or `configs/config.yaml.example`), applies `ANKIETER_*` overrides, resolves relative paths against the project root |
| `auth.py` | Login, logout and the session cookie |
| `logger.py` | Main log (file + console) and a separate rotating `ai_requests.log` |
| `data_handler.py` | `processed.json`, archiving, cache and draft directories |
| `ai/client.py` | Image preprocessing and Ollama calls (VLM, text model, re-OCR) |
| `ai/prompts.py` | Builds prompts from the `prompts` config section |
| `ai/tracing.py` | Optional LangSmith runs around VLM, text model and I/O steps |
| `domain/field_specs.py` | The 70 survey fields: name, label, page, type, choices, range, CSV header. Single source of truth for the form, validation and CSV |
| `domain/schemas.py` | `MedicalSurvey` Pydantic model, normalization, CSV row |
| `domain/csv_export.py` | Rebuilds the results CSV from verified surveys |
| `ingestion/file_grouping.py` | Scans the image directory and groups files into surveys |
| `routers/api.py` | REST API |
| `worker/` | `ProcessingWorker` and `ProcessingState` (survey statuses, progress, ETA) |

### Authentication

A single password (`app.password`) protects the app. The backend refuses to start when
it is empty. A successful login sets an HTTP-only `session_token` cookie, signed with
HMAC-SHA256, with an 8-hour cookie lifetime. The signing key is generated at startup, so a server
restart logs everyone out. All `/api` routes except `/api/auth/*` require the cookie.

### Survey discovery

`scan_survey_directory()` lists `.jpg`, `.jpeg`, `.png` and `.webp` files in
`app.surveys_dir`, sorts them by file name and splits them into groups of
`ingestion.survey_group_size` (5). Each group is one survey; its index in the list is the
survey ID, and its position in the group is the page number.

### Processing pipeline

`POST /api/processing/start` starts `ProcessingWorker` as an asyncio task. The worker
processes queued surveys one at a time, up to the requested batch size (0 = all). For
each page of a survey, `AIClient` does the following:

1. **Preprocess the image**: convert to RGB, scale the longer side down to
   `image.max_dimension` pixels, encode as PNG and base64.
2. **Extract text with the VLM**: `POST /api/chat` with the page's `vlm` prompt. Output
   that is empty, `[PUSTA_STRONA]` or shorter than 10 characters marks an empty page,
   which is skipped.
3. **Format JSON with the text model**: `POST /api/chat` with `format: "json"` and the
   `text_format` prompt, which embeds the VLM output and the page's
   `page_N_json_schema`.
4. **Re-OCR (optional)**: when the share of filled fields on the page is below
   `processing.re_ocr_threshold`, the page goes through steps 2-3 again, up to
   `processing.re_ocr_max_attempts` times.

Each Ollama request is tried up to `ai.max_retries` times, with exponential backoff between attempts. A
page that still fails is left empty. The page results are then merged (the first
non-null value of each field wins) and validated with `MedicalSurvey.from_ai_json()`:

- radio answers must match one of the allowed choices, ignoring case and surrounding
  whitespace; other values are dropped;
- numbers are parsed from the text, and a value outside the field's range (age 18-80)
  is dropped so the reviewer fills it in;
- free text is trimmed.

If a survey fails as a whole, the worker tries it up to
`processing.worker_max_retries` times, with exponential backoff between attempts, and
then marks it `error`. `POST /api/processing/stop` stops the worker after the current survey.

The worker updates progress after every step. The ETA is the average of the last
`processing.eta_rolling_window` page times multiplied by the remaining pages, for the
whole queue and for the current batch.

### Survey statuses

```
queued ──▶ processing ──▶ ready ──(save)──▶ verified
                     └──▶ error ──(save)──┘    │
                                ready ◀──(unverify)
```

- `ready`, `error` and `verified` surveys can be opened in the verification view.
- Saving validates the values again on the server. Empty values (including empty
  strings) are allowed. Invalid choices, invalid numbers or numbers out of range return
  `422` with the list of errors, unless the request sets `force: true`. A forced save
  stores invalid choices and invalid numbers as empty and keeps out-of-range numbers.
- A verified survey is read-only until it is unverified.

### Persistence

All runtime data lives under `working_vault/` (paths are configurable):

| Path | Content |
|---|---|
| `processed.json` | Session state: status, AI result (replaced by the verified values on save), error and verification time of each survey, plus recent page times |
| `survey_cache/drafts/survey_<id>.json` | Server copy of the form draft of each survey |
| `wyniki.csv` | Results CSV, rebuilt on finalize and on export |
| `archive/<YYYYMMDD-HHMMSS>/` | `processed.json` and the CSV of each cleared session |
| `logs/` | `ankieter.log`, `ai_requests.log`, script and uvicorn logs |
| `dist/` | Frontend build copied by `run_prod.ps1` / `run_prod.sh` |

On startup (or on the first `GET /api/surveys`) the state is loaded from
`processed.json`. A cached survey is reused only if its file names are unchanged; otherwise it goes back to
`queued`. `POST /api/session/clear` moves `processed.json` and the CSV to a new
`archive/<YYYYMMDD-HHMMSS>/` directory (a `-2`, `-3`, … suffix is added if the name is taken),
deletes the drafts and resets the state. Older archives are never overwritten or deleted.

### CSV export

`rebuild_csv_from_processed()` writes every verified survey from `processed.json`, in
survey order, to the results CSV: UTF-8 with BOM, `;` as the separator. The first
column is a timestamp (`M/D/YYYY HH:MM:SS`, the time the survey was verified, stored as `verified_at` in `processed.json`; for older entries without it, the time the CSV was rebuilt), followed by the 70 fields in this order:
demographics, MFIS 1-21, health, Athens Insomnia Scale, CES-D. Headers are the Polish
question texts from `field_specs.py`.

Both `POST /api/session/finalize` and `GET /api/surveys/export/csv` rebuild the whole
file, so a survey that was unverified and saved again appears only once.

## API

All routes are under `/api`. Every route except `/api/auth/*` requires the session
cookie.

| Method | Path | Description |
|---|---|---|
| GET | `/api/auth/health` | Health check |
| POST | `/api/auth/login` | Log in with `{"password": ...}`; sets the session cookie |
| POST | `/api/auth/logout` | Clear the session cookie |
| GET | `/api/field-specs` | Definitions of all 70 fields |
| GET | `/api/surveys` | Surveys found in the image directory, with status |
| GET | `/api/surveys/{id}/pages/{page}/image` | Image of one page (ETag, not cached) |
| GET | `/api/surveys/{id}/result` | AI result, saved draft and error of a processed survey |
| POST | `/api/surveys/{id}/draft` | Save the form draft |
| POST | `/api/surveys/{id}/save` | Validate and mark the survey as verified (`force` skips validation errors) |
| POST | `/api/surveys/{id}/unverify` | Return a verified survey to `ready` |
| GET | `/api/surveys/export/csv` | Rebuild and download the CSV |
| POST | `/api/processing/start` | Start the worker with `{"batch_size": n}` (0 = all) |
| GET | `/api/processing/status` | Progress, current survey, page and stage, ETA |
| POST | `/api/processing/stop` | Stop after the current survey |
| POST | `/api/session/finalize` | Rebuild the CSV from all verified surveys |
| POST | `/api/session/clear` | Archive the session and start over |

## Frontend (`src/frontend`)

React 19, TypeScript, Vite 8, React Router, TanStack Query, Zustand and Tailwind CSS.

| Route | Screen |
|---|---|
| `/login` | Password login |
| `/welcome` | Survey counts, batch size slider with ETA, start / next batch / start over, CSV download |
| `/app` | Progress bar and verification view |
| `/complete` | CSV download after finishing the session, and "Nowa sesja" (new session) |

- `api/client.ts` wraps `fetch` and redirects to `/login` on `401`. `api/hooks.ts`
  holds the TanStack Query hooks. The survey list is polled every 2 seconds while any
  survey is queued or processing, and the processing status while the worker runs.
- The verification view shows page tabs and the page image on the left and the form on
  the right. The form is generated from `/api/field-specs`, with a layout per page that
  follows the paper survey.
- Form values are resolved in this order: local draft, server draft, AI result. The
  local draft lives in the Zustand store and is written to `localStorage` 500 ms after
  the last change. `useDraftSync` sends it to the server 2 seconds after the last
  change, and immediately when the user switches survey.
- Saving validates the values in the browser first: allowed choices, whole numbers and
  ranges. Empty fields are allowed. Errors from the browser or from a server `422` are
  shown under the fields and in a banner above the form that lists the pages with
  errors. The banner has a "Zatwierdź mimo błędów" (save despite errors) button that
  saves with `force: true`.
- Conditional fields (see [survey-structure.md](survey-structure.md)) are hidden while
  their condition is not met. A conditional field that already holds a value stays
  visible, with a warning that the condition is not met, so no value is hidden.
- The Space key saves the current survey and moves to the next one, unless the focus is
  in an input.
- "Zakończ sesję" (finish session) calls `/api/session/finalize` and opens `/complete`.
- "Rozpocznij od nowa" (start over) on `/welcome` and "Nowa sesja" (new session) on
  `/complete` ask for confirmation, then call `/api/session/clear` and clear the local
  drafts. "Rozpocznij od nowa" also starts processing again; "Nowa sesja" opens
  `/welcome`. Each clear creates a new timestamped archive; older ones are kept.
