from datetime import datetime

import pytest

from booking.application.commands import CancelReservation
from booking.application.handlers import CancelReservationHandler
from booking.domain.events import ReservationCancelled
from booking.domain.model import (
    PartySize,
    ReservationAggregate,
    ReservationStatus,
    TableId,
    TimeSlot,
)
from booking.infrastructure.uow import InMemoryUnitOfWork


@pytest.fixture
def uow():
    return InMemoryUnitOfWork()


@pytest.fixture
def reservation():
    # Каждый тест получает свою бронь, чтобы изменения не влияли на другие тесты.
    return ReservationAggregate.create(
        reservation_id="r-1",
        slot=TimeSlot(
            start=datetime(2030, 1, 1, 19, 0),
            end=datetime(2030, 1, 1, 20, 30),
        ),
        party_size=PartySize(3),
    )


def save_reservation(uow, reservation):
    # Подготовка фиксирует исходную бронь до операции, которую проверяет тест.
    with uow:
        uow.reservations.add(reservation)
        uow.commit()


@pytest.mark.parametrize("confirmed", [False, True], ids=["created", "confirmed"])
def test_cancel_reservation_saves_cancelled_status(uow, reservation, confirmed):
    if confirmed:
        reservation.assign_table(TableId("T1"))
        reservation.confirm()
    save_reservation(uow, reservation)

    result = CancelReservationHandler(uow)(CancelReservation(reservation.id))

    # Проверяем сохранённое состояние и событие, а не только вызов метода cancel.
    saved = uow.reservations.get(reservation.id)
    assert saved is not None
    assert saved.status == ReservationStatus.CANCELLED
    assert saved.slot == reservation.slot
    assert saved.party_size == reservation.party_size
    assert saved.table_id == reservation.table_id
    assert uow.committed is True
    assert result is None
    cancelled_events = [
        event for event in saved.events if isinstance(event, ReservationCancelled)
    ]
    assert len(cancelled_events) == 1
    assert cancelled_events[0].reservation_id == reservation.id


def test_cancel_reservation_rejects_unknown_id(uow, reservation):
    save_reservation(uow, reservation)
    original_events = tuple(reservation.events)

    with pytest.raises(LookupError):
        CancelReservationHandler(uow)(CancelReservation("missing"))

    # До вызова был commit подготовки; новая неуспешная операция его не наследует.
    assert uow.committed is False
    assert uow.reservations.get("missing") is None
    saved = uow.reservations.get(reservation.id)
    assert saved is not None
    assert saved.status == ReservationStatus.CREATED
    assert tuple(saved.events) == original_events


def test_cancel_reservation_rejects_completed_reservation(uow, reservation):
    reservation.assign_table(TableId("T1"))
    reservation.confirm()
    reservation.mark_completed()
    save_reservation(uow, reservation)
    original_events = tuple(reservation.events)

    with pytest.raises(ValueError, match="COMPLETED"):
        CancelReservationHandler(uow)(CancelReservation(reservation.id))

    # Ошибка домена проходит через UoW; читаем результат после восстановления копии.
    saved = uow.reservations.get(reservation.id)
    assert saved is not None
    assert saved.status == ReservationStatus.COMPLETED
    assert tuple(saved.events) == original_events
    assert uow.committed is False


def test_cancel_reservation_is_idempotent(uow, reservation):
    reservation.assign_table(TableId("T1"))
    reservation.confirm()
    save_reservation(uow, reservation)
    handler = CancelReservationHandler(uow)
    command = CancelReservation(reservation.id)
    handler(command)
    saved = uow.reservations.get(reservation.id)
    assert saved is not None
    events_after_first_cancel = tuple(saved.events)

    handler(command)

    saved = uow.reservations.get(reservation.id)
    assert saved is not None
    assert saved.status == ReservationStatus.CANCELLED
    assert uow.committed is True
    # Повторный запрос не добавляет второе событие отмены и не меняет прежние события.
    assert tuple(saved.events) == events_after_first_cancel
    assert sum(isinstance(event, ReservationCancelled) for event in saved.events) == 1
