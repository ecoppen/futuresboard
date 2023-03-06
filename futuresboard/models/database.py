import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    String,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.orm import (  # type: ignore
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    Session,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func
from typing_extensions import Annotated

log = logging.getLogger(__name__)


class Base(MappedAsDataclass, DeclarativeBase):
    pass


intpk = Annotated[int, mapped_column(primary_key=True)]
strpk = Annotated[str, mapped_column(primary_key=True)]


class Database:
    def __init__(self, config) -> None:
        if config.engine == "postgres":
            engine_string = f"{config.username}:{config.password}@{config.host}:{config.port}/{config.name}"
            self.engine = create_engine("postgresql+psycopg://" + engine_string)
        elif config.engine == "sqlite":
            if config.name == "":
                self.engine = create_engine("sqlite:///:memory:")
            else:
                self.engine = create_engine(
                    "sqlite:///" + config.name + ".db?check_same_thread=false"
                )
        else:
            raise Exception(f"{config.engine} setup has not been defined")

        log.info(f"{config.engine} loaded")

        self.Base = Base

        class Accounts(self.Base):  # type: ignore
            __tablename__ = "accounts"

            id: Mapped[intpk] = mapped_column(init=False)
            name: Mapped[str]
            exchange: Mapped[str]

            positions: Mapped[List["Positions"]] = relationship(back_populates="account")  # type: ignore # noqa: F821
            orders: Mapped[List["Orders"]] = relationship(back_populates="account")  # type: ignore # noqa: F821

            added: Mapped[int] = mapped_column(
                BigInteger, default=self.timestamp(dt=datetime.now())
            )
            last_checked: Mapped[int] = mapped_column(
                BigInteger,
                default=self.timestamp(dt=datetime.now()),
                onupdate=self.timestamp(dt=datetime.now()),
            )

        class Positions(self.Base):  # type: ignore
            __tablename__ = "positions"

            id: Mapped[intpk] = mapped_column(init=False)
            account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
            symbol: Mapped[str]
            unrealised_profit: Mapped[float]
            leverage: Mapped[float]
            entry_price: Mapped[float]
            side: Mapped[str]
            amount: Mapped[float]
            liquidation_price: Mapped[float]

            account: Mapped["Accounts"] = relationship(back_populates="positions")

            added: Mapped[int] = mapped_column(
                BigInteger, default=self.timestamp(dt=datetime.now())
            )

        class Orders(self.Base):  # type: ignore
            __tablename__ = "order"

            id: Mapped[intpk] = mapped_column(init=False)
            account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
            quantity: Mapped[float]
            price: Mapped[float]
            side: Mapped[str]
            position_side: Mapped[str]
            status: Mapped[str]
            symbol: Mapped[str]

            type: Mapped[str]

            account: Mapped["Accounts"] = relationship(back_populates="orders")

            added: Mapped[int] = mapped_column(
                BigInteger, default=self.timestamp(dt=datetime.now())
            )

        self.Base.metadata.create_all(self.engine)  # type: ignore
        log.info("database tables loaded")

    def timestamp(self, dt) -> int:
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

    def get_table_object(self, table_name: str):
        self.Base.metadata.reflect(bind=self.engine)  # type: ignore
        return self.Base.metadata.tables[table_name]  # type: ignore

    def delete_then_update_positions(self, account_id: int, data: dict):
        table_object = self.get_table_object(table_name="positions")

        with Session(self.engine) as session:
            check = session.scalars(
                select(table_object).filter_by(id=account_id).limit(1)
            ).first()

            if check is not None:
                if check > 0:
                    log.info(f"Position data found for account {account_id} - deleting")
                    filters = []
                    filters.append(table_object.c.id == account_id)
                    session.execute(delete(table_object).where(*filters))
            for item in data:
                item["id"] = account_id
            session.execute(insert(table_object), data)
            session.commit()
        log.info(f"Position data updated for {account_id} - positions: {len(data)}")
