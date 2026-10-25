from contextlib import nullcontext
from datetime import datetime

import pytest

from booking.domain.model import (
    PartySize,
    ReservationAggregate,
    ReservationStatus,
    Table,
    TableId,
    TimeSlot,
)
from booking.infrastructure.uow import InMemoryUnitOfWork


def make_reservation(reservation_id):
    return ReservationAggregate.create(
        reservation_id=reservation_id,
        slot=TimeSlot(
            start=datetime(2030, 1, 1, 19, 0),
            end=datetime(2030, 1, 1, 20, 30),
        ),
        party_size=PartySize(3),
    )


def test_uow_commits_tables_and_reservations_together():
    uow = InMemoryUnitOfWork()
    reservation = make_reservation("r-1")

    with uow:
        uow.tables.add(Table(TableId("T1"), capacity=4))
        uow.reservations.add(reservation)
        uow.commit()

    saved_table = uow.tables.get(TableId("T1"))
    saved_reservation = uow.reservations.get("r-1")
    assert saved_table is not None
    assert saved_table.capacity == 4
    assert saved_reservation is not None
    assert saved_reservation.status == ReservationStatus.CREATED
    assert uow.committed is True


@pytest.mark.parametrize("fail", [False, True], ids=["without-commit", "exception"])
def test_uow_restores_both_repositories(fail):
    uow = InMemoryUnitOfWork()
    reservation = make_reservation("r-1")
    reservation.assign_table(TableId("T1"))
    reservation.confirm()
    original_events = tuple(reservation.events)
    with uow:
        uow.tables.add(Table(TableId("T1"), capacity=4))
        uow.reservations.add(reservation)
        uow.commit()

    # Один сценарий проверяется с ошибкой и при обычном выходе без commit.
    expected_exit = pytest.raises(RuntimeError) if fail else nullcontext()
    with expected_exit:
        with uow:
            existing = uow.reservations.get("r-1")
            assert existing is not None
            existing.cancel()
            uow.reservations.add(make_reservation("r-2"))
            uow.tables.add(Table(TableId("T1"), capacity=6))
            uow.tables.add(Table(TableId("T2"), capacity=2))
            if fail:
                raise RuntimeError("Operation interrupted")

    # Новый get читает восстановленные копии; старые ссылки не перематываются.
    restored_reservation = uow.reservations.get("r-1")
    restored_table = uow.tables.get(TableId("T1"))
    assert restored_reservation is not None
    assert restored_reservation.status == ReservationStatus.CONFIRMED
    assert tuple(restored_reservation.events) == original_events
    assert restored_table is not None
    assert restored_table.capacity == 4
    assert uow.reservations.get("r-2") is None
    assert uow.tables.get(TableId("T2")) is None
    assert uow.committed is False
