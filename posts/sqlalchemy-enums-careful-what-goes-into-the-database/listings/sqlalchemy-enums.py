#!/usr/bin/env python
# sqlalchemy-enums.py
# Note: you need to at least install `pip install sqlalchemy` for this to work.

from enum import Enum

import sqlalchemy
from sqlalchemy.orm import Mapped, DeclarativeBase, Session, mapped_column
from sqlalchemy import create_engine, select, text

import typing as t


class EnumWithUnknown(sqlalchemy.Enum):
    def __init__(self, *enums, **kw: t.Any):
        super().__init__(*enums, **kw)
        # SQLAlchemy sets the _adapted_from keyword argument sometimes, which contains a reference to the original type - but won't include
        # original keyword arguments, so we need to handle that here.
        self._unknown_value = (
            kw["_adapted_from"]._unknown_value
            if "_adapted_from" in kw
            else kw.get("unknown_value", None)
        )
        if self._unknown_value is None:
            raise ValueError("unknown_value should be a member of the enum")

    # This is the function which resolves the object for the DB value
    def _object_value_for_elem(self, elem):
        try:
            return self._object_lookup[elem]
        except LookupError:
            return self._unknown_value


class Color(Enum):
    UNKNOWN = "unknown"
    LEGACY_RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Base(DeclarativeBase):
    pass


class TestTable(Base):
    __tablename__ = "test_table"
    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[Color] = mapped_column(
        EnumWithUnknown(
            Color,
            values_callable=lambda t: [str(item.value) for item in t],
            unknown_value=Color.UNKNOWN,
        )
    )


engine = create_engine("sqlite://")

Base.metadata.create_all(engine)

with Session(engine) as session:
    # Create normal values
    for enum_item in [Color.LEGACY_RED, Color.GREEN, Color.BLUE]:
        session.add(TestTable(value=enum_item))
    session.commit()

with Session(engine) as session:
    session.add(TestTable(value="reed"))
    session.commit()

# Now try and read the values back
with Session(engine) as session:
    records = session.scalars(select(TestTable)).all()
    print("We restored the following values in code...")
    for record in records:
        print(record.value)

print("But the underlying table contains...")
with engine.connect() as conn:
    print(conn.execute(text("SELECT * FROM test_table;")).all())
