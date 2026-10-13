# Private Notes API

A Flask backend with session authentication, bcrypt password hashing,
user-owned notes, CRUD operations, pagination, and CSRF protection.

## Requirements

- Python 3.12
- Pipenv
- Git

## Installation

```bash
git clone https://github.com/Macrinejangu/Flask-Backend--Productivity-App.git
cd Flask-Backend--Productivity-App
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install pipenv
pipenv install --dev
```

## Database Setup

```bash
cd server
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
flask --app app db upgrade
python seed.py
```

Migrations are included. Seeding replaces existing users and notes
with two demonstration users and three notes.

Demo credentials:

- cate / StudyPass123!
- alex / NotesPass123!

These credentials are for local demonstrations only.

## Run

From server, with SECRET_KEY set:

```bash
flask --app app run --port 5555
```

The API runs at http://127.0.0.1:5555.

The default database is SQLite. DATABASE_URL overrides its location.
Keep SECRET_KEY private and stable across restarts to preserve sessions.
The export command above generates a new key each time it runs.

## Authentication and CSRF

Clients must preserve the session cookie.

Before any POST, PATCH, or DELETE request:

1. GET /csrf-token.
2. Read csrf_token from the JSON response.
3. Send the token in the X-CSRF-Token header.

Signup and login establish a session.
Signup, login, and logout clear the previous session and CSRF token.
Fetch a fresh CSRF token after each successful action.

GET /check_session returns the current user or HTTP 401.

Passwords are bcrypt-hashed. Responses expose only user ID and username.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | / | Welcome message |
| GET | /csrf-token | Get a session-bound CSRF token |
| POST | /signup | Register and log in |
| POST | /login | Log in |
| DELETE | /logout | Clear the session |
| GET | /check_session | Retrieve the authenticated user |
| GET | /notes | List the current user's notes with pagination |
| GET | /notes/<id> | Retrieve an owned note |
| POST | /notes | Create an owned note |
| PATCH | /notes/<id> | Update an owned note |
| DELETE | /notes/<id> | Delete an owned note |

## Request Bodies

Signup and login:

```json
{
  "username": "newuser",
  "password": "ExamplePass123!"
}
```

Create a note:

```json
{
  "title": "Study plan",
  "content": "Review Flask authentication."
}
```

Partial update:

```json
{
  "title": "Updated study plan"
}
```

Send JSON bodies with Content-Type: application/json.
Clients must not submit user_id. Ownership comes from the session.

## Pagination

Example:

```text
GET /notes?page=1&per_page=10
```

The response includes items, page, per_page, total, pages,
has_next, and has_prev.

The default page size is 10. The maximum is 100.
Pagination totals include only the authenticated user's notes.

## Validation and Access Control

- Usernames are normalized to lowercase and must be unique.
- Usernames contain 3 to 50 characters.
- Passwords require at least 8 characters and at most 72 UTF-8 bytes.
- Notes require a non-empty title and content.
- Titles contain at most 100 characters.
- All notes routes require authentication.
- Other users' notes return 404.
- Unknown input fields are rejected.

## Status Codes

- 200: Successful retrieval, login, or update
- 201: User or note created
- 204: Logout or deletion completed
- 400: Invalid input
- 401: Authentication required or invalid credentials
- 403: Missing or invalid CSRF token
- 404: Resource unavailable
- 409: Username unavailable
- 415: Unsupported request content type

## Tests

From the project root:

```bash
python -m pytest tests -q
```

Tests use isolated in-memory databases.
They cover authentication, password protection, username uniqueness,
CRUD, ownership isolation, pagination, and CSRF validation.

The lab's pinned pytest and Werkzeug versions produce deprecation
warnings under Python 3.12.

## Frontend Integration

The frontend must retain cookies and send CSRF headers.
For fetch requests, use credentials: "include".

The provided course frontend has not been verified against this backend.
A frontend on a separate origin also needs an explicitly configured
CORS policy allowing credentials and the X-CSRF-Token header.

## Deployment Considerations

Use HTTPS and SESSION_COOKIE_SECURE=True when deploying.
The Flask development server is intended for local development.
Login rate limiting is not implemented.