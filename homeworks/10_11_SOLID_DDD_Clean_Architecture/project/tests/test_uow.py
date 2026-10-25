from datetime import datetime

import pytest

from booking.domain.model import (
    TimeSlot,
    ReservationAggregate,
    PartySize,
    TableId,
    ReservationStatus,
)
from booking.infrastructure.uow import InMemoryUnitOfWork


def test_uow_discards_added_reservation_on_error():
    uow = InMemoryUnitOfWork()

    slot = TimeSlot(
        start=datetime(2030, 1, 1, 19, 0),
        end=datetime(2030, 1, 1, 20, 30),
    )
    reservation = ReservationAggregate.create(
        reservation_id="r-1",
        slot=slot,
        party_size=PartySize(3),
    )

    # Исключение сначала проходит через выход UoW, затем перехватывается тестом.
    with pytest.raises(RuntimeError):
        with uow:
            uow.reservations.add(reservation)
            raise RuntimeError("Операция прервана")
    assert uow.reservations.get(reservation.id) is None


def test_uow_discards_added_reservation_without_commit():
    uow = InMemoryUnitOfWork()

    slot = TimeSlot(
        start=datetime(2030, 1, 1, 19, 0),
        end=datetime(2030, 1, 1, 20, 30),
    )
    reservation = ReservationAggregate.create(
        reservation_id="r-1",
        slot=slot,
        party_size=PartySize(3),
    )

    # Нормальный выход без commit тоже должен отменить добавление.
    with uow:
        uow.reservations.add(reservation)
    assert uow.reservations.get(reservation.id) is None


def test_uow_restores_previous_state_without_commit():
    uow = InMemoryUnitOfWork()

    slot = TimeSlot(
        start=datetime(2030, 1, 1, 19, 0),
        end=datetime(2030, 1, 1, 20, 30),
    )

    reservation = ReservationAggregate.create(
        reservation_id="r-1",
        slot=slot,
        party_size=PartySize(3),
    )

    reservation.assign_table(TableId("T-1"))    # назначили стол
    reservation.confirm()                       # подтвердили бронь

    # Первая операция фиксирует исходную бронь, которую откат обязан сохранить.
    with uow:
        uow.reservations.add(reservation)
        uow.commit()

    # Повторно используем UoW: меняем старую бронь и добавляем новую без commit.
    with uow:
        existing = uow.reservations.get(reservation.id)
        assert existing is not None
        # get вернул хранимый объект: его отмена сразу меняет рабочее состояние.
        existing.cancel()

        new_reservation = ReservationAggregate.create(
            reservation_id="r-2",
            slot=slot,
            party_size=PartySize(2),
        )

        uow.reservations.add(new_reservation)

    # rollback заменил репозиторий копией; старые ссылки всё ещё видят отменённый объект.
    restored = uow.reservations.get(reservation.id)
    assert restored is not None
    assert restored.status == ReservationStatus.CONFIRMED

    assert uow.reservations.get(new_reservation.id) is None
