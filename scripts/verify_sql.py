"""Execute every reviewed SQL query against the configured DB backend."""

from sqlalchemy import text
from app.database.session import engine
from app.utils.config import ROOT

if __name__ == "__main__":
    with engine.connect() as connection:
        for path in sorted((ROOT / "sql").glob("*.sql")):
            rows = connection.execute(text(path.read_text())).fetchall()
            print(f"{path.name}: {len(rows)} rows")
