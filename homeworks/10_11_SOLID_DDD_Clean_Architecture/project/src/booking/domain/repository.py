from __future__ import annotations

from typing import Protocol, Optional, List

from .model import Reservation, TimeSlot


# Repository Port (выходной порт)
class ReservationRepository(Protocol):
    def get(self, reservation_id: str) -> Optional[Reservation]: ...
    def add(self, reservation: Reservation) -> None: ...
    def list_for_slot(self, slot: TimeSlot) -> List[Reservation]: ...
