from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Capability(Base):
    """Herstellerneutrale Security Capability, z. B. 'MFA', 'Network Segmentation'."""

    __tablename__ = "capability"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
