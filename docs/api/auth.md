# Authentication API

All endpoints are under `/api/v1/auth/`.

## Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "your-password"
}
```

Response (201):
```json
{
    "id": "uuid",
    "email": "user@example.com"
}
```

## Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "your-password"
}
```

Response (200):
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
        "id": "uuid",
        "email": "user@example.com"
    }
}
```

## Get Current User

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

Response (200):
```json
{
    "sub": "uuid",
    "email": "user@example.com"
}
```

## Using the Token

For authenticated API calls (stream links, torrent management), include the token:

```http
GET /api/v1/torrents/stream/{file_id}
Authorization: Bearer <access_token>
```
