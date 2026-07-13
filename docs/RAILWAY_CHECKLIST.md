# Railway release checklist

## API service

- `APP_ENV=production`
- `CORS_ORIGINS=https://tqproject-production-web.up.railway.app`
- `SUPABASE_URL` is set
- `SUPABASE_SERVICE_ROLE_KEY` is set only on the API service
- `MARKET_DATA_PROVIDER=yahoo` or `stooq`
- Public domain points to the API service port supplied through `$PORT`
- `/health` returns `ready: true` and all checks are `true`

## Web service

- `VITE_API_BASE_URL=https://tqproject-production-api.up.railway.app`
- `VITE_SUPABASE_URL` is set
- `VITE_SUPABASE_ANON_KEY` is set
- Supabase Auth Site URL is the production web URL
- Supabase redirect URLs contain the production web URL, not localhost

## Release verification

1. Sign up or sign in with a non-owner test account.
2. Confirm that the account cannot read the owner's strategies.
3. Recommend and adopt one strategy, then reload the page.
4. Open Today Decision and verify the QQQ data date.
5. Run one backtest and confirm data notes and scenario warnings are visible.
6. Delete the test strategy and sign out.
