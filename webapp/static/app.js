const form = document.getElementById("submit-form");
const submitBtn = document.getElementById("submit-btn");

const progressSection = document.getElementById("progress");
const stageText = document.getElementById("stage-text");

const errorSection = document.getElementById("error");
const errorText = document.getElementById("error-text");

const resultSection = document.getElementById("result");
const readmeRender = document.getElementById("readme-render");
const downloadBtn = document.getElementById("download-btn");

const STAGE_LABELS = {
  queued: "Queued…",
  cloning: "Cloning repository…",
  initializing: "Scanning repository (repodocs init)…",
  summarizing: "Summarizing files with the LLM…",
  generating: "Finalizing README…",
};

let pollTimer = null;
let currentReadme = "";

function resetPanels() {
  progressSection.hidden = true;
  errorSection.hidden = true;
  resultSection.hidden = true;
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function showError(message) {
  resetPanels();
  errorText.textContent = message;
  errorSection.hidden = false;
  submitBtn.disabled = false;
}

function showProgress(status, detail) {
  progressSection.hidden = false;
  errorSection.hidden = true;
  resultSection.hidden = true;
  const label = STAGE_LABELS[status] || status;
  stageText.textContent = detail ? `${label} — ${detail}` : label;
}

function showResult(readmeContent) {
  resetPanels();
  currentReadme = readmeContent;
  const rawHtml = marked.parse(readmeContent);
  readmeRender.innerHTML = DOMPurify.sanitize(rawHtml);
  resultSection.hidden = false;
  submitBtn.disabled = false;
}

async function pollJob(jobId) {
  try {
    const res = await fetch(`api/jobs/${jobId}`);
    if (!res.ok) {
      showError(`Lost track of this job (HTTP ${res.status}).`);
      return;
    }
    const job = await res.json();

    if (job.status === "done") {
      showResult(job.readme_content);
    } else if (job.status === "error") {
      showError(job.error || "Something went wrong.");
    } else {
      showProgress(job.status, job.stage_detail);
    }
  } catch (err) {
    showError(`Network error while checking job status: ${err}`);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetPanels();
  submitBtn.disabled = true;

  const repoUrl = document.getElementById("repo_url").value.trim();
  const groqApiKey = document.getElementById("groq_api_key").value;

  showProgress("queued", "");

  try {
    const res = await fetch("api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl, groq_api_key: groqApiKey }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      showError(body.detail || `Request failed (HTTP ${res.status}).`);
      return;
    }

    const { job_id } = await res.json();
    pollTimer = setInterval(() => pollJob(job_id), 2000);
    pollJob(job_id);
  } catch (err) {
    showError(`Network error while submitting: ${err}`);
  }
});

downloadBtn.addEventListener("click", () => {
  const blob = new Blob([currentReadme], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "README.md";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// A page restored from the browser's back-forward cache (bfcache) resumes the
// exact frozen JS state it had before navigating away — including a live
// pollTimer and a visible progress panel from a prior submission in this same
// tab. Force the UI back to a clean, un-submitted state whenever that happens.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    resetPanels();
    form.reset();
    submitBtn.disabled = false;
  }
});
