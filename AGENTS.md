# Repository Guidelines

## Project Structure & Module Organization
Primary logic lives in `src/ai_procedure_generator/`, grouped into provider integrations, validators, context managers, templating, and progressive learning flows. Shared contracts such as `Procedure` and `ProgressionAssessment` reside in `src/models/` for reuse. Runtime demos sit in `demo_*/`, while quick behaviour checks are available through `example_usage.py` and `example_procedure_management.py`. Mirror module layout inside `tests/` to keep test intent discoverable.

## Build, Test, and Development Commands
Install dependencies with `pip install -r requirements.txt`. Validate template and provider wiring via `python example_usage.py`. Run the full regression suite using `python -m pytest tests -v`; add `--maxfail=1` when triaging failures. Track coverage with `pytest --cov=src --cov-report=term-missing`. Before pushing, align formatting and typing by running `black src tests`, `flake8 src tests`, and `mypy src`.

## Coding Style & Naming Conventions
Target Python 3.9+ with Black defaults (4 spaces, 88 character lines). Packages and modules use snake_case, classes use PascalCase, and variables/functions stay snake_case. Declare constants in UPPER_SNAKE_CASE close to their use. Prefer dataclasses or TypedDicts in `src/models/` over ad hoc dicts when modelling structured data.

## Testing Guidelines
Adopt pytest with files named `test_<feature>.py` and functions beginning with `test_`. Parameterize matrices via `@pytest.mark.parametrize` and store shared fixtures in `tests/conftest.py`. Maintain at least 85% coverage for `generator.py`, `validators.py`, and progression assessment code. When editing Jinja templates, assert that generated procedures include expected phase headings and safety checks.

## Commit & Pull Request Guidelines
Write imperative, concise commit summaries (e.g., `Add progressive learning smoke tests`) and document executed verification commands in the body. Pull requests should state intent, outline system impacts—especially virtualization or networking—and link related issues. Include logs or screenshots whenever user-visible outputs change. Flag reviewers explicitly when touching `context_manager.py` or any validator module.

## Security & Configuration Tips
Do not commit environment secrets, SSH material, or host-specific libvirt settings; rely on `.env` files or OS secret stores. Treat everything under `demo_*/` as a template—copy it before experimentation. If you adjust progression gates or network defaults, document the new criteria in the PR so downstream automation stays reproducible.
