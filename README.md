# TQ Project

TQ Project is a personal investment strategy coach focused on the QQQ 200-day moving average and TQQQ risk control.

The app is designed to help a user compare and manage rules such as:

- QQQ 200-day moving average trend filter
- TQQQ/QLD exposure control
- QQQM or SPYM as a 1x buffer
- SGOV/CASH as defense or execution reserve
- staged buy/sell records
- saved strategy management
- backtests and scenario checks

> This app is an educational strategy review tool. It is not financial advice and does not guarantee returns.

## Production URLs

- Web: https://tqproject-production-web.up.railway.app
- API: https://tqproject-production-api.up.railway.app
- API health: https://tqproject-production-api.up.railway.app/health

## Core Philosophy

The current strategy philosophy is documented here:

- [Final TQQQ strategy philosophy](docs/01_strategy_philosophy/final_strategy_philosophy_2026-07-07.md)

Short version:

1. Use QQQ, not TQQQ, as the main 200-day moving average signal.
2. Above the 200-day line, participate in the market but cap effective leverage by QQQ/MA200 distance.
3. Use one 1x buffer by default: QQQM for Nasdaq-100 participation, SPYM for broader S&P 500 balance.
4. Treat staged TQQQ buying as execution discipline, not an alpha engine.
5. Use SGOV/CASH mainly for below-MA200 defense, extreme overheat, or near-term execution reserves.
6. Use backtests to compare rule robustness, not to predict future returns.

## Project Structure

```txt
apps/
  api/      FastAPI backend
  web/      React + Vite frontend
supabase/   migrations and seed data
docs/       philosophy, plans, and coding guidelines
```

## Local Development

### Backend

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7000
```

Health check:

```txt
http://localhost:7000/health
```

### Frontend

```powershell
cd apps/web
npm install
npm run dev
```

Local web:

```txt
http://localhost:4173
```

## Backtest Data

- Prices come from Yahoo Finance (dividend-adjusted close, full daily history
  back to QQQ inception in 1999), with Stooq as fallback.
- Daily snapshots are cached under `apps/api/data/market_cache/` so the same
  backtest is reproducible within a day and survives provider outages.
- TQQQ (2010-) and QLD (2006-) are extended before their inception with a
  synthetic series built from QQQ daily returns times leverage minus expense
  and financing costs, so the 2000-2002 and 2008 crashes are always included.
  Validate the model against real ETF history with:

```powershell
cd apps/api
python -m scripts.validate_synthetic
```

## Required Environment Variables

### API service

- `APP_ENV`
- `APP_NAME`
- `CORS_ORIGINS`
- `MARKET_DATA_PROVIDER`
- `OPENAI_MODEL`
- `AI_MAX_OUTPUT_TOKENS`
- `AI_REQUEST_TIMEOUT_SECONDS`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Web service

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

For Railway production, `VITE_API_BASE_URL` should point to:

```txt
https://tqproject-production-api.up.railway.app
```

## Quality Checks

Backend:

```powershell
cd apps/api
python -m pytest
```

Frontend:

```powershell
cd apps/web
npm run build
```

## Current QA Priorities

1. Browser flow: login -> strategy recommendation -> adopt strategy -> manage strategy -> test lab.
2. Mobile and narrow viewport layout check.
3. Supabase row-level security and user data separation review.
4. Stored-strategy backtest accuracy improvement.
5. README and operational notes kept in sync with deployment.

