from __future__ import annotations

from typing import Iterable, Mapping

from .model import Reservation, TableId


# Domain Service = доменная логика, не принадлежащая одной сущности.
class TableAllocationService:
    def allocate(self, reservation: Reservation, available_tables: Iterable[Mapping]) -> TableId:
        """
        Выбираем стол для брони.

        available_tables: iterable of mappings like:
          {"id": "T1", "capacity": 4}

        В реальном проекте это мог бы быть запрос в Seating Context,
        но внутри Booking мы потребляем лишь нужную проекцию (Published Language).
        """
        suitable = [
            t for t in available_tables
            if int(t["capacity"]) >= reservation.party_size.value
        ]
        if not suitable:
            raise ValueError("No suitable table available")

        chosen = min(suitable, key=lambda t: int(t["capacity"]))
        return TableId(str(chosen["id"]))
