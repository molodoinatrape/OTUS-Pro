from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from .model import Reservation, TimeSlot, PartySize


# Factory = создание агрегата так, чтобы он стартовал валидным
class ReservationFactory:
    @staticmethod
    def create(slot_start: datetime, duration_min: int, party_size: int) -> Reservation:
        reservation_id = str(uuid.uuid4())
        slot = TimeSlot(start=slot_start, end=slot_start + timedelta(minutes=duration_min))
        ps = PartySize(party_size)
        return Reservation(reservation_id=reservation_id, slot=slot, party_size=ps)
