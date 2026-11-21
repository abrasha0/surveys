# AnkieterAI

AnkieterAI digitizes paper surveys. Local AI models served by [Ollama](https://ollama.com/)
read photos of filled-in survey pages, and a person checks and corrects the result in a
side-by-side web interface before it is exported to CSV.

The app is built for a five-page Polish medical questionnaire (demographics, Athens
Insomnia Scale, MFIS and CES-D; 70 fields in total). The user interface, AI prompts and
CSV headers are in Polish.

## Features

- Two-step extraction per page: a vision model (VLM) reads the raw text from the image,
  then a text model turns it into JSON for that page's fields.
- Optional re-OCR: a page with too few filled fields is read again.
- Background worker that processes surveys one at a time, with retries, an ETA and
  batches of a chosen size. Surveys can be verified while the next ones are processed.
- Verification view with the page image next to a form generated from the field
  definitions. Invalid values are highlighted before saving and a survey can still be
  approved despite them; follow-up fields (for example "Inne") appear only when they
  apply. The Space key saves and moves to the next survey.
- Drafts are kept in the browser and synced to the server, so edits survive
  navigation, reloads and a different browser.
- CSV export (UTF-8 with BOM, `;` separator) that opens directly in Excel.
- Session state is stored on disk, so processing results survive a server restart.
- Single-password login and an optional public Cloudflare tunnel.
- Optional LangSmith tracing of AI calls.

## Requirements

- Windows (PowerShell scripts), or macOS / Linux (bash scripts)
- Python 3.12 or newer
- Node.js 20.19+ or 22.12+ with npm (required by Vite 8)
- Ollama. On Windows `full_setup.ps1` installs it if it is missing; on macOS and Linux
  install it first (`brew install ollama` or <https://ollama.com/download>)
- `curl` (macOS / Linux scripts)
- A GPU is recommended. The default models (`qwen3-vl:8b` and `llama3.1`) target GPUs
  with at least 8 GB of VRAM; `configs/config.yaml.light` uses `moondream` and
  `llama3.2:3b` for weaker hardware.

## Quick start

Windows (PowerShell):

```powershell
# 1. Create the configuration and set app.password in it
Copy-Item configs\config.yaml.example config.yaml

# 2. One-time setup: .venv, Python and npm packages, Ollama, AI models
.\scripts\full_setup.ps1

# 3. Put the survey photos in working_vault\surveys_data

# 4. Start the app
.\scripts\run_prod.ps1             # production build + public Cloudflare tunnel
.\scripts\run_prod.ps1 -NoTunnel   # local only
```

macOS / Linux (bash):

```bash
# 1. Create the configuration and set app.password in it
cp configs/config.yaml.example config.yaml

# 2. One-time setup: .venv, Python and npm packages, Ollama server, AI models
scripts/full_setup.sh

# 3. Put the survey photos in working_vault/surveys_data

# 4. Start the app
scripts/run_prod.sh               # production build + public Cloudflare tunnel
scripts/run_prod.sh --no-tunnel   # local only
```

Open `http://localhost:8000` and log in with the password from `config.yaml`.

Images are sorted by file name and split into groups of five, one image per page, so
name the files in page order (for example `001_1.jpg` … `001_5.jpg`).
Supported formats: JPG, PNG and WebP.

## Scripts

Each script has a PowerShell version (`.ps1`, Windows) and a bash version (`.sh`, macOS
and Linux) that do the same steps.

| Script | When | What it does |
|---|---|---|
| `scripts/full_setup` | Once (safe to re-run) | Checks Python and Node.js, creates `.venv`, installs Python and npm packages, starts Ollama, pulls and tests the models from the config. `-Force` / `--force` recreates `.venv`. |
| `scripts/run_prod` | Every production run | Builds the frontend into `working_vault/dist`, starts uvicorn on port 8000 and opens a Cloudflare tunnel. |
| `scripts/run_dev` | Development | Deletes `working_vault/logs` (including the server-side drafts in `logs/survey_cache`), then starts uvicorn with `--reload` on port 8000 and the Vite dev server on port 5173. Restarts the backend when the image directory changes, or when you press `R`. |

`run_prod` parameters:

- `-NoTunnel` / `--no-tunnel` skips the Cloudflare tunnel.
- `-CloudflaredDir <dir>` / `--cloudflared-dir <dir>`: where `cloudflared` is looked up
  when it is not in `PATH`.
  - Windows (default `C:\tools`): if `cloudflared.exe` is not found there either, the
    script downloads it to this directory and adds the directory to the user `PATH`.
  - macOS / Linux (default `~/.local/bin`): the script does not download anything and
    stops with an install hint (`brew install cloudflared` or the Linux packages from
    Cloudflare).

Differences of the bash scripts: `full_setup.sh` does not install Ollama (the Linux
installer needs root, and on macOS Ollama is an app or a Homebrew package), but it starts
`ollama serve` when the server is not running. It looks for Python as `python3.13`,
`python3.12`, `python3` and `python`; set `PYTHON=/path/to/python3.12` to choose one.

The tunnel URL is printed to the console and saved to `working_vault/logs/tunnel_url.txt`.
Script logs are written to `working_vault/logs/`.

## Configuration

The backend reads `config.yaml` from the project root. Copy one of the profiles in
`configs/` and set `app.password`; the backend refuses to start without a password.

| Profile | Description |
|---|---|
| `configs/config.yaml.example` | Template with comments for every key: `qwen3-vl:8b` + `llama3.1`, re-OCR enabled |
| `configs/config.yaml.light` | Small models (`moondream` + `llama3.2:3b`), re-OCR disabled |
| `configs/config.yaml.prod` | Production profile; currently the same settings as the template |

Any key can be overridden with an environment variable named
`ANKIETER_<SECTION>_<KEY>`, for example `ANKIETER_APP_PASSWORD` or
`ANKIETER_AI_VLM_MODEL`. Only keys present in the YAML file can be overridden.

Two retry levels are configurable: `ai.max_retries` is the number of attempts for a single
Ollama request, and `processing.worker_max_retries` the number of attempts for a whole survey.

The prompts and the per-page JSON schemas live in the `prompts` section of the config.
When you change the survey fields, update both `src/backend/domain/field_specs.py` and
the matching `page_N_json_schema` prompt.

To enable LangSmith tracing, set `langsmith.tracing_v2: true`, `langsmith.endpoint` and
`langsmith.api_key`.

## Development

Run the backend and frontend without the scripts (any OS). Create `config.yaml` with a
password first, as in the quick start.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # .venv\Scripts\pip on Windows
cd src/backend && ../../.venv/bin/python -m uvicorn main:app --reload --port 8000

# in another terminal
cd src/frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to port 8000
npm run lint
npm run build
```

`requirements-dev.txt` adds pytest; the repository has no automated tests yet.

## Architecture

```
React + Vite (src/frontend) ──REST /api──▶ FastAPI (src/backend) ──▶ background worker ──▶ Ollama
                                                │                                      (VLM + text model)
                                                └─▶ working_vault/: processed.json, drafts, CSV, logs
```

In production FastAPI also serves the built frontend. The frontend polls the processing
status every 2 seconds while the worker runs. See [docs/architecture.md](docs/architecture.md)
for the processing pipeline, the API and the data files, and
[docs/survey-structure.md](docs/survey-structure.md) for all survey fields.

## Project structure

```
configs/            configuration profiles (copy one to config.yaml)
docs/               architecture and survey structure
scripts/            setup and run scripts: PowerShell (Windows) and bash (macOS, Linux)
src/backend/        FastAPI app
  ai/               Ollama client, prompts, LangSmith tracing
  domain/           field definitions, survey model, CSV export
  ingestion/        image directory scanning
  routers/          REST API
  worker/           background worker and processing state
src/frontend/       React app (Vite, TypeScript, TanStack Query, Zustand, Tailwind CSS)
working_vault/      runtime data, not in git: images, results, logs, frontend build
```
