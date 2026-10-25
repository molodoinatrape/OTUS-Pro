from datetime import datetime

import pytest

from booking.application.commands import CancelReservation, CreateReservation
from booking.application.handlers import CancelReservationHandler, CreateReservationHandler
from booking.domain.model import (
    PartySize,
    ReservationAggregate,
    ReservationStatus,
    Table,
    TableId,
    TimeSlot,
)
from booking.domain.services import TableAllocationService
from booking.infrastructure.repositories import InMemoryReservationRepository
from booking.infrastructure.uow import InMemoryUnitOfWork


def command(hour, minute=0, duration=90):
    return CreateReservation(datetime(2030, 1, 1, hour, minute), duration, 3)


@pytest.fixture
def uow():
    work = InMemoryUnitOfWork()
    with work:
        work.tables.add(Table(TableId("T1"), capacity=4))
        work.commit()
    return work


@pytest.mark.parametrize(
    "hour, minute, duration",
    [(19, 0, 90), (20, 0, 90), (18, 30, 60), (19, 30, 30), (18, 0, 240)],
    ids=["same", "overlap-end", "overlap-start", "inside", "contains"],
)
def test_overlapping_booking_is_rejected_without_changing_existing_booking(
    uow, hour, minute, duration
):
    handler = CreateReservationHandler(uow, TableAllocationService())
    original_id = handler(command(19))
    original = uow.reservations.get(original_id)
    assert original is not None
    original_events = tuple(original.events)

    # Единственный подходящий стол уже занят подтверждённой бронью.
    with pytest.raises(ValueError, match="No suitable table"):
        handler(command(hour, minute, duration))

    saved = uow.reservations.get(original_id)
    assert saved is not None
    assert saved.status == ReservationStatus.CONFIRMED
    assert tuple(saved.events) == original_events
    assert uow.committed is False
    assert len(uow.tables.list_all()) == 1
    assert [r.id for r in uow.reservations.list_overlapping(saved.slot)] == [original_id]


def test_overlapping_booking_uses_another_free_table(uow):
    with uow:
        uow.tables.add(Table(TableId("T2"), capacity=6))
        uow.commit()
    handler = CreateReservationHandler(uow, TableAllocationService())
    first_id = handler(command(19))

    second_id = handler(command(20))

    first = uow.reservations.get(first_id)
    second = uow.reservations.get(second_id)
    assert first is not None and second is not None
    assert first.table_id == TableId("T1")
    assert second.table_id == TableId("T2")


@pytest.mark.parametrize("hour, minute", [(17, 30), (20, 30)], ids=["before", "after"])
def test_adjacent_bookings_can_use_the_same_table(uow, hour, minute):
    handler = CreateReservationHandler(uow, TableAllocationService())
    handler(command(19))

    # Равенство конца одной брони началу другой не считается пересечением.
    new_id = handler(command(hour, minute))

    saved = uow.reservations.get(new_id)
    assert saved is not None
    assert saved.table_id == TableId("T1")
    assert saved.status == ReservationStatus.CONFIRMED


def test_cancelled_booking_releases_table_for_an_overlapping_booking(uow):
    handler = CreateReservationHandler(uow, TableAllocationService())
    first_id = handler(command(19))
    CancelReservationHandler(uow)(CancelReservation(first_id))

    new_id = handler(command(20))

    cancelled = uow.reservations.get(first_id)
    saved = uow.reservations.get(new_id)
    assert cancelled is not None and saved is not None
    assert cancelled.status == ReservationStatus.CANCELLED
    assert saved.table_id == TableId("T1")
    assert saved.status == ReservationStatus.CONFIRMED


def test_repository_returns_partial_overlaps_and_excludes_adjacent_slots():
    repository = InMemoryReservationRepository()
    for reservation_id, start_hour, end_hour in [
        ("overlapping", 19, 21),
        ("adjacent", 18, 20),
        ("later", 22, 23),
    ]:
        repository.add(
            ReservationAggregate.create(
                reservation_id,
                TimeSlot(datetime(2030, 1, 1, start_hour), datetime(2030, 1, 1, end_hour)),
                PartySize(3),
            )
        )

    found = repository.list_overlapping(
        TimeSlot(datetime(2030, 1, 1, 20), datetime(2030, 1, 1, 22))
    )

    # Поиск пересечений не должен требовать полного совпадения границ.
    assert [reservation.id for reservation in found] == ["overlapping"]
