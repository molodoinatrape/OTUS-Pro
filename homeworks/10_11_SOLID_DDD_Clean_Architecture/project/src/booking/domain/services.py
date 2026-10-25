from __future__ import annotations

from typing import Iterable

from .model import ReservationAggregate, TableId, Table


# Domain Service = доменная логика, не принадлежащая одной сущности.
class TableAllocationService:
    def allocate(
            self,
            reservation: ReservationAggregate,
            available_tables: Iterable[Table]
    ) -> TableId:
        """Подобрать стол наименьшей достаточной вместимости среди объектов Table.

        Кандидаты передаются вызывающей стороной. Проверяется только вместимость,
        занятость по времени не учитывается. При отсутствии кандидата - ValueError.
        """
        suitable = [
            t for t in available_tables
            if t.can_fit(reservation.party_size)
        ]
        if not suitable:
            raise ValueError("No suitable table available")

        chosen = min(suitable, key=lambda t: t.capacity)

        return chosen.id
