"""Reset the database by dropping all tables and recreating them from SQLAlchemy models.

WARNING: This will irreversibly delete ALL data. Use only in development or after a backup.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add project root

from database import engine, Base, init_db


def main():
    print("WARNING: This will DROP ALL TABLES and DELETE ALL DATA in the database.")
    confirm = input("Type 'yes' to continue: ")
    if confirm.strip().lower() != "yes":
        print("Aborted. No changes made.")
        return

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables from models...")
    init_db()
    print("Database reset complete.")


if __name__ == "__main__":
    main()
