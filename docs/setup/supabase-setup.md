# Supabase Setup

## 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click **New project**
3. Choose organization, name (e.g. `laura-suite`), and database password
4. Select region closest to you
5. Wait for provisioning (~2 minutes)

## 2. Get API Keys

In Project Dashboard → **Project Settings** → **API**:

| Key | Where to put it |
|-----|----------------|
| **Project URL** (e.g. `https://xyz.supabase.co`) | `SUPABASE_URL` in `.env` |
| **anon public** key | `VITE_SUPABASE_ANON_KEY` in `laura_suite_fe/.env` |
| **service_role** key | `SUPABASE_SERVICE_KEY` in `laura_suite_be/.env` |
| **JWT Secret** (Settings → API → JWT Settings) | `SUPABASE_JWT_SECRET` in `laura_suite_be/.env` |

## 3. Configure Auth

Go to **Authentication → Providers**:

- **Email**: Enabled by default
- **Disable "Confirm email"** (optional) — set under Email settings → Confirm email = off
- Disable all other providers (GitHub, Google, etc.)

## 4. Create the Profiles Table

Go to **SQL Editor** and run:

```sql
create table public.profiles (
    id uuid references auth.users on delete cascade primary key,
    email text,
    role text default 'user',
    created_at timestamptz default now()
);

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

## 5. Set Admin Role

After registering your first user, make them admin:

```sql
update public.profiles
set role = 'admin'
where email = 'your-email@example.com';
```

## 6. Verify Connection

```powershell
# Test auth
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email","password":"your-password"}'

# Should return: {"access_token": "eyJ...", "user": {...}}
```
