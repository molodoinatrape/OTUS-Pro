from __future__ import annotations

from booking.application.unit_of_work import UnitOfWork
from booking.infrastructure.repositories import InMemoryReservationRepository


class InMemoryUnitOfWork(UnitOfWork):
    """UoW для тестов/демо без БД."""

    def __init__(self) -> None:
        self.reservations = InMemoryReservationRepository()
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


# Заготовка под SQLAlchemy UoW (для лекции / дальнейшего расширения)
class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self.session = None
        self.reservations = None

    def __enter__(self):
        self.session = self._session_factory()
        # self.reservations = SqlAlchemyReservationRepository(self.session)
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb):
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError
