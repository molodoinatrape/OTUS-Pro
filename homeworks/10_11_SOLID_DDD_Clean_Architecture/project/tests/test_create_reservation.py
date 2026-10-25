from datetime import datetime, timedelta

import pytest

from booking.application.commands import CreateReservation
from booking.application.handlers import CreateReservationHandler
from booking.domain.model import Table, TableId, TimeSlot
from booking.domain.services import TableAllocationService
from booking.infrastructure.uow import InMemoryUnitOfWork


def test_create_reservation_happy_path():
    uow = InMemoryUnitOfWork()
    # Передаём сценарию хранилище и алгоритм выбора стола извне.
    handler = CreateReservationHandler(uow, TableAllocationService())

    # Каталог сохранён до запроса; первым идёт подходящий, но слишком большой стол.
    with uow:
        uow.tables.add(Table(TableId("T3"), capacity=6))
        uow.tables.add(Table(TableId("T1"), capacity=2))
        uow.tables.add(Table(TableId("T2"), capacity=4))
        uow.commit()

    cmd = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0, 0),
        duration_min=90,
        party_size=3,
    )

    # Вызов экземпляра запускает __call__: создать, назначить, подтвердить, сохранить.
    reservation_id = handler(cmd)

    assert reservation_id
    assert uow.committed is True

    # Проверяем результат в репозитории, а не только возвращённый идентификатор.
    saved = uow.reservations.get(reservation_id)
    assert saved is not None
    assert saved.status.value == "CONFIRMED"
    assert saved.table_id.value == "T2"


def test_timeslot_invariant_enforced():
    uow = InMemoryUnitOfWork()
    handler = CreateReservationHandler(uow, TableAllocationService())

    # end раньше start -> должно упасть при создании слота во Factory
    cmd = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0, 0),
        duration_min=-10,
        party_size=2,
    )

    # Проверяем именно отказ TimeSlot, а не случайную ошибку пустого каталога.
    with pytest.raises(ValueError, match="start must be < end"):
        handler(cmd)


@pytest.mark.parametrize("capacities", [(), (2,)], ids=["empty", "too-small"])
def test_create_reservation_rejects_catalog_without_suitable_tables(capacities):
    uow = InMemoryUnitOfWork()
    with uow:
        for index, capacity in enumerate(capacities):
            uow.tables.add(Table(TableId(f"T{index}"), capacity=capacity))
        uow.commit()
    handler = CreateReservationHandler(uow, TableAllocationService())
    command = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0),
        duration_min=90,
        party_size=3,
    )

    with pytest.raises(ValueError, match="No suitable table"):
        handler(command)

    slot = TimeSlot(command.slot_start, command.slot_start + timedelta(minutes=90))
    assert uow.reservations.list_for_slot(slot) == []
    assert len(uow.tables.list_all()) == len(capacities)
    assert uow.committed is False
