# Root API (controllers/root.py)

Endpoint

- GET `/` — simple health/root endpoint.
  - Response: `{"message": "Hello, World!"}`
  - Use for quick sanity check that the server is running.

Example:

```bash
curl http://localhost:8000/
# => {"message":"Hello, World!"}
```
