# Repository Guidelines

## Project Structure & Module Organization
This repository is a Django 4.2 application for sales planning and approval workflows. Core business logic lives under `core/`:

- `core/users/` handles authentication, profiles, departments, and roles.
- `core/products/` manages brands, categories, and SKU data.
- `core/plans/` contains sales plan submission, detail rows, and reporting.
- `core/approvals/` implements approval flow and history.

Project configuration is in `config/` (`settings.py`, `urls.py`, `wsgi.py`). Shared templates are in `templates/`, grouped by feature, with HTMX partials under `templates/**/partials/`. Static assets live in `static/`, and collected production assets are written to `staticfiles/`. The default local database is `db_new.sqlite3`.

## Build, Test, and Development Commands
Set up and run locally with standard Django commands:

- `python -m venv venv` and `venv\Scripts\activate` to create and activate a virtual environment on Windows.
- `pip install -r requirements.txt` to install Django, HTMX helpers, Tailwind tooling, and data libraries.
- `python manage.py migrate` to apply schema changes.
- `python manage.py runserver` to start the development server.
- `python manage.py test` to run the current test suite.
- `python manage.py makemigrations` to generate migrations after model changes.
- `python manage.py collectstatic` to build deployable static assets.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation. Use `PascalCase` for models and class-based types, `snake_case` for functions, URL names, and template context keys. Keep Django templates feature-scoped, for example `templates/plans/plan_detail.html`, and place HTMX fragments in `partials/`. Prefer small view functions, `select_related()`/`prefetch_related()` for query-heavy pages, and keep business rules in models or dedicated helpers rather than templates.

## Testing Guidelines
There is no dedicated `tests/` package yet, so add tests next to each app using `tests.py` or `tests/` within `core/<app>/`. Name test methods `test_<behavior>`. Cover model rules, view permissions, and approval/status transitions. Run `python manage.py test core.plans core.approvals` when touching workflow logic.

## Commit & Pull Request Guidelines
Recent history uses short, imperative subjects, often prefixed with `feat:` or `docs:`. Keep the first line focused on one change, for example `feat: add SKU import validation`. Pull requests should include a brief summary, affected modules, migration notes if models changed, and screenshots for template or dashboard updates. Link the related issue or task when available.

## Security & Configuration Tips
Do not commit real secrets. `config/settings.py` currently contains a development `SECRET_KEY`, `DEBUG = True`, and permissive `ALLOWED_HOSTS`; production deployments should override these with environment-specific values.
