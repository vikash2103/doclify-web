import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from webapp import jobs

BASE_DIR = Path(__file__).resolve().parent


class PrefixMiddleware:
    """
    Strips a URL prefix (e.g. "/repodocs") from incoming requests before
    Starlette's routing sees them, for deployments where the reverse proxy
    forwards the full path unchanged rather than stripping it itself. Set via
    the APP_ROOT_PATH env var; a no-op when it's unset (e.g. local dev).

    Deliberately does not set scope["root_path"] — this app's templates use
    plain relative paths rather than url_for(), and setting root_path here
    breaks Starlette's StaticFiles mount routing (confirmed: identical
    already-stripped scope["path"], 200 with root_path unset, 404 with it set).
    """

    def __init__(self, app, prefix: str):
        self.app = app
        self.prefix = prefix.rstrip("/")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self.prefix and scope["path"].startswith(self.prefix):
            scope["path"] = scope["path"][len(self.prefix):] or "/"
        await self.app(scope, receive, send)


app = FastAPI(title="RepoDocs")

root_path = os.environ.get("APP_ROOT_PATH", "").rstrip("/")
if root_path:
    app.add_middleware(PrefixMiddleware, prefix=root_path)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


class SubmitRequest(BaseModel):
    repo_url: str
    groq_api_key: str


class SubmitResponse(BaseModel):
    job_id: str


@app.post("/api/submit", response_model=SubmitResponse)
def submit(payload: SubmitRequest, background_tasks: BackgroundTasks):
    repo_url = payload.repo_url.strip()
    groq_api_key = payload.groq_api_key.strip()

    if not jobs.is_valid_github_url(repo_url):
        raise HTTPException(status_code=422, detail="repo_url must look like https://github.com/<owner>/<repo>")
    if not groq_api_key:
        raise HTTPException(status_code=422, detail="groq_api_key is required")

    job_id = jobs.create_job(repo_url)
    background_tasks.add_task(jobs.run_pipeline, job_id, repo_url, groq_api_key)
    return SubmitResponse(job_id=job_id)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")

    return {
        "status": job["status"],
        "stage_detail": job["stage_detail"],
        "readme_content": job["readme_content"],
        "error": job["error"],
    }
