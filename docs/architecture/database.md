# Database

## Supabase (Cloud, PostgreSQL)

Laura Suite uses **Supabase** for authentication and data storage. Supabase provides:

- **Auth** — email/password authentication with JWT tokens
- **PostgreSQL** — relational database for user profiles and application data
- **Row Level Security** — per-user data isolation

## Schema

```sql
-- User profiles (mirrors auth.users)
create table public.profiles (
    id uuid references auth.users on delete cascade primary key,
    email text,
    role text default 'user',
    created_at timestamptz default now()
);

-- Auto-create profile on signup
create function public.handle_new_user()
returns trigger as $$
begin
    insert into public.profiles (id, email, role)
    values (new.id, new.email, 'user');
    return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();
```

## Auth Flow

```
Client                    Supabase                    Backend
  │                         │                          │
  │── POST /auth/register──►│                          │
  │                         │── create user ──────────►│
  │◄── { id, email } ──────┤                          │
  │                         │                          │
  │── POST /auth/login ────►│                          │
  │◄── { access_token } ───┤                          │
  │                         │                          │
  │── GET /torrents/stream ─┤── Bearer JWT ───────────►│
  │                         │                          │── verify JWT
  │                         │                          │── return stream URL
  │◄── { url } ────────────┤──────────────────────────┤
```

## Local SQLite

The backend also uses SQLite (`/data/laura.db`) for operational data that doesn't need multi-user access (torrent history, scan logs). This runs inside the Docker container and is gitignored.
