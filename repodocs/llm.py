import os
import re

from groq import Groq

from repodocs.prompts import build_file_summary_prompt, build_readme_prompt


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return Groq(api_key=api_key)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:markdown|md)?\s*(.*?)\s*```$", text, re.DOTALL)
    return match.group(1).strip() if match else text


def summarize_file(client: Groq, model: str, file_path: str, content: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": build_file_summary_prompt(file_path, content)}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def generate_readme(client: Groq, model: str, project_name: str, file_summaries: dict[str, str]) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": build_readme_prompt(project_name, file_summaries)}],
        temperature=0,
    )
    return _strip_code_fence(response.choices[0].message.content)
