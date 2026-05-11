# AGENTS.md

## Cursor Cloud specific instructions

### Repository overview

This is a Python-based repository used primarily for generating PowerPoint presentations via `python-pptx`. The `main` branch is a scaffold (`.gitkeep` only); feature branches contain the actual application code (Python scripts + `requirements.txt`).

### Environment

- **Python 3.12** is available system-wide.
- Dependencies are installed via `pip install -r requirements.txt` (when `requirements.txt` exists on the active branch).
- The primary dependency is `python-pptx` (and its transitive deps: `lxml`, `Pillow`, `XlsxWriter`).

### Running the application

- Feature branches (e.g. `cursor/orthodox-supervision-presentation-bad3`) contain a `generate_presentation.py` script.
- The script writes output to a subdirectory specified by its `OUT` path constant. Ensure that directory exists before running.
- Example: `mkdir -p супервизия && python3 generate_presentation.py`

### Lint / Test / Build

- No linter, test framework, or build system is configured on `main` at this time.
- If a feature branch introduces `requirements.txt`, install with `pip install -r requirements.txt`.

### Gotchas

- The `.env` file exists in the project but is listed in `.cursorignore`. Do not create or search for it. Use `.env.example` as a template and let the developer fill in real values.
- Output directories referenced in scripts (e.g. Cyrillic-named folders) must be created manually before running generation scripts.
