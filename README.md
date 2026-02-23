# FastAPI backend (minimal)

This is a minimal FastAPI backend. It already includes `app.py` with a single root route.

Quick start (Windows PowerShell):

1. Create a virtual environment named `.venv` in the project root:

```powershell
python -m venv .venv
```

If `python` is not available, try `py -3 -m venv .venv`.

2. Activate the virtual environment (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Upgrade pip and install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. Run the app with uvicorn (from project root):

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

If `python` shows the Microsoft Store message, disable the App execution alias or install Python from python.org and then re-open the terminal. You can also use `py -3` instead of `python` in the commands above.

Endpoint:
- GET /  — returns {"message": "Hello, World!"}

Next steps (optional):
- Add a `tests/` folder and pytest configuration.
- Add a small `start.ps1` script for convenience.
 - A `start.ps1` script has been added to the project root. Run it from PowerShell to create/activate `.venv`, install requirements and start the server:

```powershell
.\start.ps1
```
