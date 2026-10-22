from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func, UniqueConstraint, CheckConstraint, Integer, Sequence
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, declared_attr


class Base(DeclarativeBase):

    @declared_attr
    def id(cls):
        return mapped_column(Integer,
                             Sequence(f'{cls.__tablename__}_id_seq'),
                             primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 server_default=func.now(),
                                                 onupdate=func.now())


class Crop(Base):
    __tablename__ = "crops"

    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name_en: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    subspecies: Mapped[list["Subspecies"]] = relationship(
        back_populates="crop", order_by="Subspecies.name")
    markers: Mapped[list["MarkerAssociation"]] = relationship(
        back_populates="crop")


class Subspecies(Base):
    __tablename__ = "subspecies"

    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    name_en: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    crop: Mapped["Crop"] = relationship(back_populates="subspecies")
    varieties: Mapped[list["Variety"]] = relationship(
        back_populates="subspecies", order_by="Variety.name")
    markers: Mapped[list["MarkerAssociation"]] = relationship(
        back_populates="subspecies")

    __table_args__ = (UniqueConstraint("crop_id",
                                       "name",
                                       name="uq_subspecies_crop_name"), )


class Variety(Base):
    __tablename__ = "varieties"

    subspecies_id: Mapped[int] = mapped_column(ForeignKey("subspecies.id"),
                                               index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    name_en: Mapped[str | None] = mapped_column(String(200))

    subspecies: Mapped["Subspecies"] = relationship(back_populates="varieties")
    markers: Mapped[list["MarkerAssociation"]] = relationship(
        back_populates="variety")

    __table_args__ = (UniqueConstraint("subspecies_id",
                                       "name",
                                       name="uq_variety_subspecies_name"), )


class Marker(Base):
    __tablename__ = "markers"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name_en: Mapped[str | None] = mapped_column(String(200))
    structure_formula: Mapped[str | None] = mapped_column(String(200))

    associations: Mapped[list["MarkerAssociation"]] = relationship(
        back_populates="marker",
        primaryjoin="Marker.id == foreign(MarkerAssociation.marker_id)",
    )


class MarkerAssociation(Base):
    __tablename__ = "marker_associations"

    marker_id: Mapped[int] = mapped_column(Integer, index=True)

    crop_id: Mapped[int | None] = mapped_column(ForeignKey("crops.id"),
                                                index=True)
    subspecies_id: Mapped[int | None] = mapped_column(
        ForeignKey("subspecies.id"), index=True)
    variety_id: Mapped[int | None] = mapped_column(ForeignKey("varieties.id"),
                                                   index=True)

    source: Mapped[str | None] = mapped_column(String(200))
    screening_method: Mapped[str | None] = mapped_column(String(200))
    metabolic_pathway: Mapped[str | None] = mapped_column(Text)
    literature_source: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    notes2: Mapped[str | None] = mapped_column(Text)

    marker: Mapped["Marker"] = relationship(
        back_populates="associations",
        primaryjoin="foreign(MarkerAssociation.marker_id) == Marker.id",
    )
    crop: Mapped["Crop | None"] = relationship(back_populates="markers")
    subspecies: Mapped["Subspecies | None"] = relationship(
        back_populates="markers")
    variety: Mapped["Variety | None"] = relationship(back_populates="markers")

    __table_args__ = (
        CheckConstraint("""
            (crop_id IS NOT NULL AND subspecies_id IS NULL AND variety_id IS NULL) OR
            (crop_id IS NULL AND subspecies_id IS NOT NULL AND variety_id IS NULL) OR
            (crop_id IS NULL AND subspecies_id IS NULL AND variety_id IS NOT NULL)
            """,
                        name="check_single_level"),
        UniqueConstraint("marker_id",
                         "crop_id",
                         "subspecies_id",
                         "variety_id",
                         name="uq_marker_association"),
    )
