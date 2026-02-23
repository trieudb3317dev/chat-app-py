Alembic migrations for this project

Quick start:

1. Install alembic in your environment:

   pip install alembic

2. Ensure DATABASE_URL environment variable is set (or update alembic.ini):

   export DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname

3. Create an autogenerate revision:

   alembic revision --autogenerate -m "describe changes"

4. Apply the migration:

   alembic upgrade head

Notes:
- env.py is configured to import the project's `Base` from `database.py` so autogenerate
  will pick up models under `Base.metadata`.
- In development you may prefer to run `python scripts/reset_db.py` to recreate tables from models.
