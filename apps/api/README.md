# api (FastAPI)

## Run (Windows / PowerShell)

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in Supabase keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/health · Docs: http://localhost:8000/docs
`GET /me` is an example protected route (requires a Supabase bearer token → 401 without it).

## Test & lint

```powershell
pytest          # test_health.py, test_me.py
ruff check .    # config in pyproject.toml (line-length 100)
ruff format .
```

## Layout

```
app/
  main.py                          app factory (create_app), CORS, exception handlers, routers
  core/config.py                   pydantic-settings (.env)
  core/errors.py                   register_exception_handlers (safe 500, no leak)
  api/deps.py                      get_current_user (Supabase JWT) → CurrentUser / CurrentUserDep
  api/routes/health.py, me.py      thin HTTP routers (add domain routers here)
  services/supabase.py             the only backend Supabase client (service role)
  repositories/profile_repository.py  DB access (Supabase table queries)
  schemas/common.py, me.py         Pydantic request/response models
  tests/                           pytest
```

Rules: see [`docs/08_coding_guidelines/02_python_fastapi.md`](../../docs/08_coding_guidelines/02_python_fastapi.md).
