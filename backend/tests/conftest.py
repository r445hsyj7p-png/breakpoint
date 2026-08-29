import os

# Muss vor jedem app.core.*-Import gesetzt sein, damit Settings die Test-DB liest.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://breakpoint:breakpoint@localhost:5432/breakpoint_test"
)

import pytest
from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine


@pytest.fixture()
def db_session() -> Session:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
