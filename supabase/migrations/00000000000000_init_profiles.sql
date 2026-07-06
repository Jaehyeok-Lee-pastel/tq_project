-- Starter migration — profiles linked to auth.users, with RLS enabled.
--
-- This is a template example demonstrating the required pattern (RLS on +
-- owner-scoped policies + auto-provisioning). Rename/extend per project.
-- For multi-tenant apps, add a tenant table (workspaces/orgs) and scope
-- policies by membership instead of by user id.

create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text,
    display_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- RLS is mandatory on every new table.
alter table public.profiles enable row level security;

-- Owner can read their own row.
create policy "profiles_select_own" on public.profiles
    for select using (auth.uid() = id);

-- Owner can update their own row.
create policy "profiles_update_own" on public.profiles
    for update using (auth.uid() = id) with check (auth.uid() = id);

-- Auto-create a profile row when a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
    insert into public.profiles (id, email)
    values (new.id, new.email)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- Keep updated_at fresh on every update.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
    before update on public.profiles
    for each row execute function public.set_updated_at();
