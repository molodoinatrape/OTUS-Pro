from __future__ import annotations

from typing import Mapping, Iterable

from booking.application.commands import CreateReservation
from booking.application.unit_of_work import UnitOfWork
from booking.domain.factory import ReservationFactory
from booking.domain.services import TableAllocationService


class CreateReservationHandler:
    """
    Use Case (Application Service):

    - создает агрегат (Factory)
    - вызывает доменные правила (Domain Service + методы Aggregate Root)
    - сохраняет через UoW/Repository
    """

    def __init__(self, uow: UnitOfWork, allocator: TableAllocationService):
        self.uow = uow
        self.allocator = allocator

    def __call__(self, cmd: CreateReservation, available_tables: Iterable[Mapping]) -> str:
        reservation = ReservationFactory.create(
            slot_start=cmd.slot_start,
            duration_min=cmd.duration_min,
            party_size=cmd.party_size,
        )

        table_id = self.allocator.allocate(reservation, available_tables)
        reservation.assign_table(table_id)
        reservation.confirm()

        with self.uow:
            self.uow.reservations.add(reservation)
            self.uow.commit()

        return reservation.id
