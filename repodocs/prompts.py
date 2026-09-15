def build_file_summary_prompt(file_path: str, content: str) -> str:
    return (
        "You are documenting a codebase one file at a time. Read the file below "
        "and write a dense, factual summary in 3-5 sentences covering: what this "
        "file is responsible for, its key functions or classes, and what other "
        "parts of the system it likely interacts with. Base the summary only on "
        "what is actually in the file — do not guess at intent you can't see. "
        "Do not include code snippets or the words 'this file' repeatedly.\n\n"
        f"File: {file_path}\n"
        "---\n"
        f"{content}\n"
        "---\n\n"
        "Summary:"
    )


def build_readme_prompt(project_name: str, file_summaries: dict[str, str]) -> str:
    # The real per-file summaries are embedded directly in the main prompt body,
    # not appended afterward — the model has to actually read them to follow the
    # instructions below, since they're presented as the project's own context.
    context = "\n\n".join(
        f"### {path}\n{summary}" for path, summary in file_summaries.items()
    )

    return (
        "You are writing a README.md for a real software project, based only on "
        "the information below. Do not invent features, technologies, or details "
        "not reflected in it.\n\n"
        f"Project name: {project_name}\n\n"
        "Summaries of every source file in the project:\n\n"
        f"{context}\n\n"
        "---\n\n"
        "Write a complete README.md in Markdown with these sections, in order, "
        "skipping any that don't apply given the information above:\n"
        "- A top-level heading with the project name, followed by a one-line "
        "tagline describing what it does\n"
        "- An Overview paragraph explaining the purpose and what problem it solves\n"
        "- A Tech Stack section listing the languages/frameworks/libraries actually "
        "used, inferred from the file summaries\n"
        "- A Getting Started section with plausible setup/run instructions for a "
        "project of this type\n"
        "- A Project Structure section briefly describing the key files\n\n"
        "Do not add placeholder text like 'TODO' or 'Coming soon' — if there isn't "
        "enough information for a section, omit that section entirely. Output only "
        "the README content in Markdown, with no commentary before or after it."
    )
