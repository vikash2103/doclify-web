# doclify-web

A small web app that generates an AI-written `README.md` for any public GitHub repository. Paste a repo URL and a [Groq](https://console.groq.com) API key, and it clones the repo, summarizes every source file, and writes a README from those summaries — rendered in the browser with a download button.

It's built from two independent pieces:

- **`repodocs/`** — a standalone CLI tool (`repodocs init`, `repodocs run`) that does the actual work: scans a directory respecting `.gitignore`, summarizes each file via the Groq API, and generates a README from the aggregated summaries. Usable entirely on its own, outside the web app.
- **`webapp/`** — a FastAPI wrapper around `repodocs`: a form to submit a repo + key, a background job that shells out to the CLI, and a polling UI that renders the result.

## How it works

1. You submit a GitHub URL and a Groq API key through the form.
2. The server shallow-clones the repo into a temporary directory.
3. `repodocs init` scans the clone and writes a manifest of files to process.
4. `repodocs run` summarizes each file with one Groq call per file, then makes one final call with all the summaries plus the real project name to generate the README.
5. The rendered README (and a download button) appear in the browser; the temp clone and the API key are discarded once the run finishes.

The Groq key is never written to disk or logged — it only ever exists in the job's subprocess environment for the duration of that one `repodocs run` call.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use `source .venv/bin/activate` on macOS/Linux

pip install -e .                 # installs the repodocs CLI
pip install -r requirements-web.txt   # installs the web app's dependencies
```

## Running

```bash
uvicorn webapp.main:app --reload
```

Open `http://127.0.0.1:8000`, paste a repo URL and a Groq API key (get a free one at [console.groq.com](https://console.groq.com)), and submit.

## Using the CLI directly

`repodocs` doesn't require the web app — it works standalone against any local directory:

```bash
cd /path/to/some/project
export GROQ_API_KEY=your-key-here   # or set it on Windows with $env:GROQ_API_KEY
repodocs init
repodocs run
```

This writes `repodocs.yaml` (the scan manifest) and, after `run`, a generated `README.md` in that directory (backing up any existing one to `README.md.bak`).
