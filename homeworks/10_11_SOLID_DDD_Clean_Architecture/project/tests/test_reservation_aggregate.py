from datetime import datetime

import pytest

from booking.domain.model import (
    ReservationAggregate,
    TimeSlot,
    PartySize,
    ReservationStatus,
    TableId,
)


def test_confirm_updates_public_properties():
    slot = TimeSlot(
        start=datetime(2030, 1, 1, 19, 0),
        end=datetime(2030, 1, 1, 20, 30),
    )
    reservation = ReservationAggregate.create(
        reservation_id="reservation-1",
        slot=slot,
        party_size=PartySize(3),
    )

    reservation.assign_table(TableId("T1"))   # назначили стол
    reservation.confirm()                     # подтвердили бронь

    assert reservation.table_id == TableId("T1")
    assert reservation.status == ReservationStatus.CONFIRMED


def test_public_properties_reject_assignment():
    slot = TimeSlot(
        start=datetime(2030, 1, 1, 19, 0),
        end=datetime(2030, 1, 1, 20, 30),
    )
    reservation = ReservationAggregate.create(
        reservation_id="reservation-1",
        slot=slot,
        party_size=PartySize(3),
    )

    # Ошибка присваивания подтверждает отсутствие setter у публичного свойства.
    with pytest.raises(AttributeError):
        reservation.status = ReservationStatus.CONFIRMED
    assert reservation.status == ReservationStatus.CREATED

    # Отдельный блок: первое исключение не должно пропустить вторую проверку.
    with pytest.raises(AttributeError):
        reservation.table_id = TableId("T1")
    assert reservation.table_id is None
