# Users API (controllers/user.py)

Base prefix: `/api/v1`

Endpoints

1. POST /api/v1/users/register
   - Purpose: Create a new user.
   - Body (JSON):
     {
       "email": "user@example.com",
       "password": "secret",
       "name": "Display Name"
     }
   - Response: {"message": "..."}
   - Notes: Rate-limited (example: 5 requests/minute).

2. POST /api/v1/users/login
   - Purpose: Authenticate user and set auth cookies (access_token, refresh_token).
   - Body (JSON):
     {"email": "user@example.com", "password": "secret"}
   - Response: {"message": "..."}
   - Notes: Uses cookies to store tokens. When calling from the browser, include credentials so cookies are stored: `fetch(..., { credentials: 'include' })`. Rate-limited (example: 5 requests/minute).

3. POST /api/v1/users/logout
   - Purpose: Clear authentication cookies.
   - Response: {"message": "..."}
   = Note: Rate-limited (example: 5 requests/minute).

4. GET /api/v1/users/me
   - Purpose: Return current authenticated user's profile.
   - Auth: Requires `auth_required`. Server reads access token from cookie.
   - Example fetch (browser):
     ```js
     fetch('/api/v1/users/me', { credentials: 'include' })
       .then(r => r.json()).then(console.log)
     ```
    - Note: Rate-limited (example: 5 requests/minute).

6. PUT /api/v1/users/profile
   - Purpose: Update current user's profile.
   - Auth: Requires authentication.
   - Body: Partial profile fields, example: `{ "name": "New" }`
    - Note: Rate-limited (example: 5 requests/minute).

7. POST /api/v1/users/refresh-token
   - Purpose: Refresh access token from refresh cookie and set new access cookie.
   - Notes: Call this endpoint when you get 401 or on app start to refresh tokens. Use `credentials: 'include'`.
   - Note: Rate-limited (example: 5 requests/minute).

8. POST /api/v1/users/reset-password
   - Purpose: Trigger password reset (placeholder implementation). Auth required in current code.
   - Note: Rate-limited (example: 5 requests/minute).

9. POST /api/v1/users/change-password
   - Purpose: Change current user's password. Auth required.
   - Note: Rate-limited (example: 5 requests/minute).

Quick client notes
- For endpoints that set/require cookies (login, refresh, me, logout), always call with `credentials: 'include'` in the browser so cookies are sent and saved.
- Example login call with fetch:
  ```js
  fetch('/api/v1/users/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    credentials: 'include'
  })
  ```

Rate limiting
- Many endpoints have a rate limit dependency to help prevent brute-force; backend returns 429 if you exceed limits.

Schemas
- The project uses Pydantic models in `entities/schemas.py` for request/response shapes. Use the examples above for quick integration; for full shape, inspect `entities/schemas.py`.
