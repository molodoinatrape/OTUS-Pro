from __future__ import annotations

from typing import Optional, List

from booking.domain.model import Reservation, TimeSlot
from booking.domain.repository import ReservationRepository


class InMemoryReservationRepository(ReservationRepository):
    def __init__(self) -> None:
        self._items: dict[str, Reservation] = {}

    def get(self, reservation_id: str) -> Optional[Reservation]:
        return self._items.get(reservation_id)

    def add(self, reservation: Reservation) -> None:
        self._items[reservation.id] = reservation

    def list_for_slot(self, slot: TimeSlot) -> List[Reservation]:
        return [r for r in self._items.values() if r.slot == slot]


# Заготовка под SQLAlchemy (для лекции / дальнейшего расширения)
class SqlAlchemyReservationRepository(ReservationRepository):
    def __init__(self, session) -> None:
        self.session = session

    def get(self, reservation_id: str) -> Optional[Reservation]:
        raise NotImplementedError

    def add(self, reservation: Reservation) -> None:
        raise NotImplementedError

    def list_for_slot(self, slot: TimeSlot) -> List[Reservation]:
        raise NotImplementedError
