import os
import json
from datetime import datetime, timezone

def save_run(summary, filename):
    url = os.getenv("DATABASE_URL")
    if not url:
        return False, "DATABASE_URL не задан — история не сохранялась."
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS validation_runs (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL,
                    filename TEXT,
                    summary JSONB NOT NULL
                )
            """))
            conn.execute(text("""
                INSERT INTO validation_runs (created_at, filename, summary)
                VALUES (:created_at, :filename, CAST(:summary AS JSONB))
            """), {"created_at": datetime.now(timezone.utc), "filename": filename,
                   "summary": json.dumps(summary, ensure_ascii=False)})
        return True, "История проверки сохранена в PostgreSQL."
    except Exception as exc:
        return False, f"Не удалось сохранить историю: {exc}"
