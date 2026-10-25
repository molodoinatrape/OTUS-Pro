from __future__ import annotations

from booking.application.commands import CreateReservation, CancelReservation
from booking.application.unit_of_work import UnitOfWork
from booking.domain.factory import ReservationFactory
from booking.domain.model import ReservationStatus
from booking.domain.services import TableAllocationService


class CreateReservationHandler:
    """Создать подтверждённую бронь, используя каталог столов из UoW.

    Фабрика создаёт агрегат, сервис выбирает стол по вместимости, агрегат назначает
    стол и подтверждает бронь. Добавление в репозиторий подтверждается через commit.
    """

    def __init__(self, uow: UnitOfWork, allocator: TableAllocationService):
        self.uow = uow
        self.allocator = allocator

    def __call__(self, cmd: CreateReservation) -> str:
        with self.uow:
            reservation = ReservationFactory.create(
                slot_start=cmd.slot_start,
                duration_min=cmd.duration_min,
                party_size=cmd.party_size,
            )
            overlapping_reservations = self.uow.reservations.list_overlapping(
                reservation.slot
            )
            occupied_table_ids = set()
            for existing in overlapping_reservations:
                if (
                    existing.table_id is not None
                    and existing.status == ReservationStatus.CONFIRMED
                ):
                    occupied_table_ids.add(existing.table_id)

            tables = self.uow.tables.list_all()
            available_tables = []
            for table in tables:
                if table.id not in occupied_table_ids:
                    available_tables.append(table)
                    
            table_id = self.allocator.allocate(reservation, available_tables)

            reservation.assign_table(table_id)
            reservation.confirm()

            self.uow.reservations.add(reservation)
            self.uow.commit()

        return reservation.id


class CancelReservationHandler:
    """Отменить найденную бронь и подтвердить изменение через UoW.

    При неизвестном идентификаторе - LookupError. Допустимость отмены проверяет
    агрегат; при исключении неподтверждённые изменения откатываются.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def __call__(self, cmd: CancelReservation) -> None:
        with self.uow:
            reservation = self.uow.reservations.get(cmd.reservation_id)

            if reservation is None:
                raise LookupError("Reservation not found")

            reservation.cancel()
            self.uow.commit()
