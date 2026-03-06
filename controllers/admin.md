# Admin API (controllers/admin.py)

Base prefix: `/api/v1`

This controller exposes endpoints for admin user management. Many routes require authentication and specific roles (`admin` or `super_admin`).

Endpoints

1. POST /api/v1/admin/register
   - Purpose: Create a new admin account.
   - Body: same shape as user registration.
   - Notes: Rate-limited.

2. POST /api/v1/admin/login
   - Purpose: Authenticate admin and set auth cookies.
   - Body: `{ "email": "admin@example.com", "password": "..." }`
   - Response: {"message": "..."}
   - Use `credentials: 'include'` to allow cookies.

3. POST /api/v1/admin/logout
   - Purpose: Clear admin auth cookies.

4. GET /api/v1/admin/me
   - Purpose: Get profile of current admin user. Requires authentication.

5. PUT /api/v1/admin/profile
   - Purpose: Update admin profile. Requires authentication.

6. POST /api/v1/admin/refresh-token
   - Purpose: Refresh admin access token from refresh cookie.

7. POST /api/v1/admin/reset-password
   - Purpose: Trigger admin password reset (requires auth in current code).

8. POST /api/v1/admin/change-password
   - Purpose: Change admin password (requires auth).

9. DELETE /api/v1/admin/users/{user_id}
   - Purpose: Delete a regular user account. Requires `admin` or `super_admin` role.

10. GET /api/v1/admin/users
    - Purpose: List regular users (pagination via `page` and `per_page` query params). Requires admin role.

Client notes
- Follow same cookie/auth rules as the `user` controller: use `credentials: 'include'` for requests that rely on cookies.
- Role-restricted endpoints will return 403 if the caller lacks required roles.
