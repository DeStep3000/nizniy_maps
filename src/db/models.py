import uuid
from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from geoalchemy2 import Geometry


class Base(DeclarativeBase):
    pass


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    address: Mapped[str] = mapped_column(Text, nullable=False)
    coordinate = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
