from __future__ import annotations

from typing import Protocol

from booking.domain.repository import ReservationRepository


# Unit of Work Port (выходной порт)
class UnitOfWork(Protocol):
    reservations: ReservationRepository

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
