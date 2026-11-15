-- Vāk on Supabase: films shared from the Studio, render jobs, and the chant library.
-- Apply once (Supabase SQL editor, or the MCP apply_migration). The Studio writes with a secret API key (sb_secret_...) on the
-- laptop (never in the browser); the public can only read films that were shared.

create table if not exists public.chants (
  id           text primary key,                 -- e.g. "gayatri", "k:panchakshari"
  name         text not null,
  source       text,                             -- citation; null = not identified
  devanagari   text not null,
  translations jsonb not null default '{}'::jsonb,
  provenance   text not null default 'Identified' check (provenance in ('Verified', 'Identified', 'Interpreted')),
  updated_at   timestamptz not null default now()
);

create table if not exists public.films (
  id           text primary key,                 -- the Studio's film id
  title        text not null,
  chant        text,
  style        text,
  live         boolean not null default false,   -- drawn live in the player (Nāda, Liquid gold)
  duration     real,
  provenance   text,
  voice        text,                             -- e.g. "Recording", "ElevenLabs", "Neural recitation"
  video_url    text,                             -- public Storage URL of the film (MP4)
  poster_url   text,
  review       text not null default 'awaiting teacher review',
  shared_at    timestamptz not null default now()
);

create table if not exists public.jobs (
  id           text primary key,
  title        text,
  style        text,
  status       text not null,
  progress     real,
  stage        text,
  film_id      text,
  seconds      integer,
  created_at   timestamptz,
  updated_at   timestamptz not null default now()
);

alter table public.chants enable row level security;
alter table public.films  enable row level security;
alter table public.jobs   enable row level security;

-- anyone may read shared films and the chant library; nobody but the Studio (secret key) may write; jobs stay private
drop policy if exists "films are public" on public.films;
create policy "films are public" on public.films for select to anon, authenticated using (true);
drop policy if exists "chants are public" on public.chants;
create policy "chants are public" on public.chants for select to anon, authenticated using (true);

-- public bucket for shared films and posters (read by URL; uploads only with the secret key)
insert into storage.buckets (id, name, public) values ('films', 'films', true)
on conflict (id) do update set public = true;

-- table privileges (new projects don't grant them automatically); RLS above still decides which rows
grant usage on schema public to anon, authenticated, service_role;
grant select, insert, update, delete on public.films, public.chants, public.jobs to service_role;
grant select on public.films, public.chants to anon, authenticated;

-- Sign-in (2026-11-15, web/auth.py): jobs remember who started them. Users live in Supabase Auth (auth.users).
alter table public.jobs add column if not exists user_id uuid references auth.users (id) on delete set null;
create index if not exists jobs_user_id_idx on public.jobs (user_id);
