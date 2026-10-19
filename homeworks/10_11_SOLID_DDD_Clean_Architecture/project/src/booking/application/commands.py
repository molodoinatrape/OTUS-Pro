from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


# Команда = входные данные use case (Input DTO)
@dataclass(frozen=True)
class CreateReservation:
    slot_start: datetime
    duration_min: int
    party_size: int
