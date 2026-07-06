-- User-scoped storage for the TQ Coach deployment.
-- Strategy payloads are stored as JSONB so the app can keep evolving without
-- frequent destructive schema changes. RLS keeps each user's data isolated.

create table if not exists public.managed_strategies (
    id text primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    data jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.managed_strategies enable row level security;

drop policy if exists "managed_strategies_select_own" on public.managed_strategies;
create policy "managed_strategies_select_own" on public.managed_strategies
    for select using (auth.uid() = user_id);

drop policy if exists "managed_strategies_insert_own" on public.managed_strategies;
create policy "managed_strategies_insert_own" on public.managed_strategies
    for insert with check (auth.uid() = user_id);

drop policy if exists "managed_strategies_update_own" on public.managed_strategies;
create policy "managed_strategies_update_own" on public.managed_strategies
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "managed_strategies_delete_own" on public.managed_strategies;
create policy "managed_strategies_delete_own" on public.managed_strategies
    for delete using (auth.uid() = user_id);

create index if not exists managed_strategies_user_updated_idx
    on public.managed_strategies (user_id, updated_at desc);

create table if not exists public.user_settings (
    user_id uuid primary key references auth.users (id) on delete cascade,
    settings jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.user_settings enable row level security;

drop policy if exists "user_settings_select_own" on public.user_settings;
create policy "user_settings_select_own" on public.user_settings
    for select using (auth.uid() = user_id);

drop policy if exists "user_settings_insert_own" on public.user_settings;
create policy "user_settings_insert_own" on public.user_settings
    for insert with check (auth.uid() = user_id);

drop policy if exists "user_settings_update_own" on public.user_settings;
create policy "user_settings_update_own" on public.user_settings
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop trigger if exists managed_strategies_set_updated_at on public.managed_strategies;
create trigger managed_strategies_set_updated_at
    before update on public.managed_strategies
    for each row execute function public.set_updated_at();

drop trigger if exists user_settings_set_updated_at on public.user_settings;
create trigger user_settings_set_updated_at
    before update on public.user_settings
    for each row execute function public.set_updated_at();
