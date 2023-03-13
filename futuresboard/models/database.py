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

            positions: Mapped[List["Positions"]] = relationship(back_populates="account", cascade="all, delete")  # type: ignore # noqa: F821
            orders: Mapped[List["Orders"]] = relationship(back_populates="account", cascade="all, delete")  # type: ignore # noqa: F821
            wallet: Mapped[List["Wallet"]] = relationship(back_populates="account", cascade="all, delete")  # type: ignore # noqa: F821
            transactions: Mapped[List["Transactions"]] = relationship(back_populates="account", cascade="all, delete")  # type: ignore # noqa: F821

            active: Mapped[int] = mapped_column(Integer, default=1)
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
            __tablename__ = "orders"

            id: Mapped[intpk] = mapped_column(init=False)
            account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
            quantity: Mapped[float]
            price: Mapped[float]
            side: Mapped[str]
            status: Mapped[str]
            symbol: Mapped[str]
            type: Mapped[str]
            created_time: Mapped[int] = mapped_column(BigInteger)
            updated_time: Mapped[int] = mapped_column(BigInteger)

            account: Mapped["Accounts"] = relationship(back_populates="orders")

            added: Mapped[int] = mapped_column(
                BigInteger, default=self.timestamp(dt=datetime.now())
            )

        class Wallet(self.Base):  # type: ignore
            __tablename__ = "wallet"

            id: Mapped[intpk] = mapped_column(init=False)
            account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
            coin: Mapped[str]
            amount: Mapped[float]

            account: Mapped["Accounts"] = relationship(back_populates="wallet")

            added: Mapped[int] = mapped_column(
                BigInteger, default=self.timestamp(dt=datetime.now())
            )

        class Transactions(self.Base):  # type: ignore
            __tablename__ = "transactions"

            id: Mapped[intpk] = mapped_column(init=False)
            account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
            symbol: Mapped[str]
            order_id: Mapped[str]
            order_type: Mapped[str]
            exec_type: Mapped[str]
            profit: Mapped[float]
            created_time: Mapped[int] = mapped_column(BigInteger)
            updated_time: Mapped[int] = mapped_column(BigInteger)

            account: Mapped["Accounts"] = relationship(back_populates="transactions")

        self.Base.metadata.create_all(self.engine)  # type: ignore
        log.info("database tables loaded")

    def timestamp(self, dt) -> int:
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

    def get_table_object(self, table_name: str):
        self.Base.metadata.reflect(bind=self.engine)  # type: ignore
        return self.Base.metadata.tables[table_name]  # type: ignore

    def set_accounts_inactive(self) -> None:
        log.info("Setting all accounts inactive before loading config")
        table_object = self.get_table_object(table_name="accounts")
        with Session(self.engine) as session:
            session.execute(update(table_object).values({"active": 0}))
            session.commit()

    def get_latest_transaction_symbol(self, account_id: int, symbol: str) -> int:
        table_object = self.get_table_object(table_name="transactions")

        with Session(self.engine) as session:
            check = session.execute(
                select(table_object).filter_by(id=account_id, symbol=symbol).limit(1)
            ).first()

            if check is None:
                return int(
                    datetime.fromisoformat("2019-01-01 00:00:00+00:00").timestamp()
                    * 1000
                )
            else:
                return int(check[7])

    def add_get_account_ids(self, accounts: list) -> list:
        table_object = self.get_table_object(table_name="accounts")

        with Session(self.engine) as session:
            for account in accounts:
                check = session.scalars(
                    select(table_object).filter_by(name=account.name).limit(1)
                ).first()
                if check is None:
                    log.info(
                        f"Adding account named '{account.name}' using exchange '{account.exchange}' to database"
                    )
                    session.execute(
                        insert(table_object),
                        {"name": account.name, "exchange": account.exchange},
                    )
                    log.info(f"Account named '{account.name}' saved")
                    check = session.scalars(
                        select(table_object).filter_by(name=account.name).limit(1)
                    ).first()
                    account.id = check
                else:
                    log.info(
                        f"Account found in database with name '{account.name}', loading"
                    )
                    filters = [table_object.c.id == check]
                    session.execute(
                        update(table_object).where(*filters).values({"active": 1})
                    )
                    session.commit()
                    account.id = check
            session.commit()
        return accounts

    def delete_then_update_by_account_id(
        self, account_id: int, table: str, data: dict
    ) -> None:
        if table in ["positions", "orders", "wallet"]:
            table_object = self.get_table_object(table_name=table)

            with Session(self.engine) as session:
                check = session.scalars(
                    select(table_object).filter_by(account_id=account_id).limit(1)
                ).first()

                if check is not None:
                    if check > 0:
                        log.info(
                            f"{table.title()} data found for account {account_id} - deleting"
                        )
                        filters = [table_object.c.account_id == account_id]
                        session.execute(delete(table_object).where(*filters))
                if len(data) > 0:
                    for item in data:
                        item["account_id"] = account_id
                    session.execute(insert(table_object), data)
                session.commit()
            log.info(
                f"{table.title()} data updated for {account_id} - {table}: {len(data)}"
            )

    def check_then_add_transaction(self, account_id: int, data: dict) -> None:
        table_object = self.get_table_object(table_name="transactions")
        added = 0
        with Session(self.engine) as session:
            for transaction in data:
                check = session.scalars(
                    select(table_object)
                    .filter_by(
                        account_id=account_id,
                        symbol=transaction["symbol"],
                        order_id=transaction["order_id"],
                        created_time=transaction["created_time"],
                    )
                    .limit(1)
                ).first()
                if check is None:
                    transaction["account_id"] = account_id
                    session.execute(insert(table_object), transaction)
                    added += 1
            session.commit()
        log.info(f"Transaction data updated for {transaction['symbol']}: {added}")

    def get_accounts(self) -> dict:
        table_object = self.get_table_object(table_name="accounts")
        accounts: dict = {"active": [], "inactive": []}
        with Session(self.engine) as session:
            all_accounts = session.execute(
                select(table_object).order_by(table_object.c.id.asc())
            ).all()
            active = ["inactive", "active"]
            for account in all_accounts:
                positions = self.get_count_positions(account_id=account[0])
                orders = self.get_count_orders(account_id=account[0])
                upnl = self.get_unrealised_profit(account_id=account[0])
                pnl = self.get_closed_profit(account_id=account[0])
                accounts[active[account[3]]].append(
                    {
                        "id": account[0],
                        "name": account[1],
                        "exchange": account[2],
                        "last_update": account[5],
                        "long": positions["long"],
                        "short": positions["short"],
                        "buy": orders["buy"],
                        "sell": orders["sell"],
                        "upnl": upnl,
                        "pnl": pnl,
                    }
                )
        return accounts

    def get_count_positions(self, account_id: int) -> dict:
        table_object = self.get_table_object(table_name="positions")
        positions: dict = {"long": 0, "short": 0}
        with Session(self.engine) as session:
            filters = [
                table_object.c.account_id == account_id,
                table_object.c.side == "LONG",
            ]
            count_long = session.scalar(
                select(func.count()).select_from(table_object).filter(*filters)
            )

            filters = [
                table_object.c.account_id == account_id,
                table_object.c.side == "SHORT",
            ]
            count_short = session.scalar(
                select(func.count()).select_from(table_object).filter(*filters)
            )

        if count_long is not None:
            positions["long"] = count_long
        if count_short is not None:
            positions["short"] = count_short
        return positions

    def get_count_orders(self, account_id: int) -> dict:
        table_object = self.get_table_object(table_name="orders")
        orders: dict = {"buy": 0, "sell": 0}
        with Session(self.engine) as session:
            filters = [
                table_object.c.account_id == account_id,
                table_object.c.side == "BUY",
            ]
            count_buy = session.scalar(
                select(func.count()).select_from(table_object).filter(*filters)
            )

            filters = [
                table_object.c.account_id == account_id,
                table_object.c.side == "SELL",
            ]
            count_sell = session.scalar(
                select(func.count()).select_from(table_object).filter(*filters)
            )

        if count_buy is not None:
            orders["buy"] = count_buy
        if count_sell is not None:
            orders["sell"] = count_sell

        return orders

    def get_unrealised_profit(self, account_id: int) -> float:
        table_object = self.get_table_object(table_name="positions")
        with Session(self.engine) as session:
            result = session.scalar(
                select(func.sum(table_object.c.unrealised_profit))
                .select_from(table_object)
                .filter_by(account_id=account_id)
            )
        if result is None:
            return 0.0
        else:
            return result

    def get_closed_profit(self, account_id: int) -> float:
        table_object = self.get_table_object(table_name="transactions")
        with Session(self.engine) as session:
            result = session.scalar(
                select(func.sum(table_object.c.profit))
                .select_from(table_object)
                .filter_by(account_id=account_id)
            )
        if result is None:
            return 0.0
        else:
            return result
