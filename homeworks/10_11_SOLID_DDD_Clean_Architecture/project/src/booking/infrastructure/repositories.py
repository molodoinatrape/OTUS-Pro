from __future__ import annotations

from typing import Optional, List

from booking.domain.model import ReservationAggregate, TimeSlot, TableId, Table
from booking.domain.repository import ReservationRepository, TableRepository


class InMemoryReservationRepository(ReservationRepository):
    def __init__(self) -> None:
        self._items: dict[str, ReservationAggregate] = {}

    def get(self, reservation_id: str) -> Optional[ReservationAggregate]:
        return self._items.get(reservation_id)

    def add(self, reservation: ReservationAggregate) -> None:
        self._items[reservation.id] = reservation

    def list_for_slot(self, slot: TimeSlot) -> List[ReservationAggregate]:
        return [r for r in self._items.values() if r.slot == slot]

    def list_overlapping(self, slot: TimeSlot) -> List[ReservationAggregate]:
        return [
            reservation
            for reservation in self._items.values()
            if reservation.slot.overlaps(slot)
        ]


class InMemoryTableRepository(TableRepository):
    def __init__(self) -> None:
        self._items: dict[TableId, Table] = {}

    def get(self, table_id: TableId) -> Optional[Table]:
        return self._items.get(table_id)

    def add(self, table: Table) -> None:
        self._items[table.id] = table

    def list_all(self) -> List[Table]:
        return list(self._items.values())


# Заготовка под SQLAlchemy (для лекции / дальнейшего расширения)
class SqlAlchemyReservationRepository(ReservationRepository):
    def __init__(self, session) -> None:
        self.session = session

    def get(self, reservation_id: str) -> Optional[ReservationAggregate]:
        raise NotImplementedError

    def add(self, reservation: ReservationAggregate) -> None:
        raise NotImplementedError

    def list_for_slot(self, slot: TimeSlot) -> List[ReservationAggregate]:
        raise NotImplementedError
