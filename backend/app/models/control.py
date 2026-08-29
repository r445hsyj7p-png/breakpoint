import enum

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ControlCategory(str, enum.Enum):
    PREVENT = "prevent"
    DETECT = "detect"
    RESPOND = "respond"


class Control(Base):
    """Eine konkrete Maßnahme (Prevent/Detect/Respond), eigenständig und wiederverwendbar
    über mehrere Techniken/Taktik-Standards hinweg — siehe docs/projektauftrag.md Abschnitt 5."""

    __tablename__ = "control"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[ControlCategory] = mapped_column(
        Enum(ControlCategory, name="control_category"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(256), nullable=False)

    __table_args__ = (UniqueConstraint("category", "label", name="uq_control_category_label"),)
