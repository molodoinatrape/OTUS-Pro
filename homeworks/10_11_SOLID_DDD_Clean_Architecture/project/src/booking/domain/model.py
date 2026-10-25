from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from .events import (
    ReservationCreated,
    ReservationConfirmed,
    ReservationCancelled,
    TableAssigned,
)

# =============================================================================
# VALUE OBJECTS (VO)
# =============================================================================

@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError("TimeSlot invariant: start must be < end")

    def overlaps(self, other: TimeSlot) -> bool:
        if self.start < other.end and other.start < self.end:
            return True
        return False


@dataclass(frozen=True)
class PartySize:
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError("PartySize invariant: must be >= 1")


@dataclass(frozen=True)
class TableId:
    value: str


class ReservationStatus(str, Enum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


# =============================================================================
# ENTITY
# =============================================================================
# Entity = идентичность + изменяемое состояние.
# ВАЖНО: мы НЕ даём внешнему миру менять поля напрямую (это соглашение),
# а все операции делаем через Aggregate.
# =============================================================================

class Reservation:
    """
    Entity:

    - имеет устойчивую идентичность: id
    - содержит состояние: slot, party_size, table_id, status
    - сама по себе НЕ является границей согласованности.

    Граница (Aggregate) будет отдельным объектом.
    """

    def __init__(
        self,
        reservation_id: str,
        slot: TimeSlot,
        party_size: PartySize,
        table_id: Optional[TableId] = None,
        status: ReservationStatus = ReservationStatus.CREATED,
    ) -> None:
        self.id = reservation_id
        self.slot = slot
        self.party_size = party_size
        self.table_id = table_id
        self.status = status


class Table:
    table_id: TableId
    capacity: int

    def __init__(self, table_id: TableId, capacity: int) -> None:
        self._id = table_id
        if capacity <= 0:
            raise ValueError("Table capacity must be > 0")
        self._capacity = capacity

    @property
    def id(self) -> TableId:
        return self._id

    @property
    def capacity(self) -> int:
        return self._capacity

    def can_fit(self, party_size: PartySize) -> bool:
        if self.capacity >= party_size.value:
            return True
        return False


# =============================================================================
# AGGREGATE
# =============================================================================
# Aggregate = граница согласованности + инварианты + события.
#
# Aggregate Root = root-Entity, через которую внешний мир взаимодействует
# с агрегатом. Здесь root = Reservation entity.
#
# Чтобы "агрегат менялся через root", мы:
# - прячем изменения Entity за методами Aggregate
# - даём наружу внутреннее состояние только для чтения через свойства
# =============================================================================

class ReservationAggregate:
    """
    Aggregate (граница):
    - содержит root-entity Reservation
    - защищает инварианты (правила, которые должны быть истинны всегда)
    - накапливает Domain Events в self.events

    Внешний код вызывает методы агрегата, а агрегат меняет root.
    """

    def __init__(self, root: Reservation) -> None:
        self._root = root
        self.events: List[Any] = []

    # ---------- Внутреннее состояние читается через отдельные свойства ----------
    @property
    def id(self) -> str:
        return self._root.id

    @property
    def slot(self) -> TimeSlot:
        return self._root.slot

    @property
    def party_size(self) -> PartySize:
        return self._root.party_size

    @property
    def table_id(self) -> TableId | None:
        return self._root.table_id

    @property
    def status(self) -> ReservationStatus:
        return self._root.status

    # ---------- Factory-like constructor (удобно) ----------
    @classmethod
    def create(
            cls,
            reservation_id: str,
            slot: TimeSlot,
            party_size: PartySize
    ) -> "ReservationAggregate":
        root = Reservation(
            reservation_id=reservation_id,
            slot=slot,
            party_size=party_size
        )
        agg = cls(root)
        agg.events.append(ReservationCreated(root.id, datetime.now(timezone.utc)))
        return agg

    # ---------- Operations (изменяют root и защищают инварианты) ----------

    def assign_table(self, table_id: TableId) -> None:
        # Invariant: assignment only when CREATED
        if self._root.status != ReservationStatus.CREATED:
            raise ValueError("Invariant: can assign table only for CREATED reservation")

        self._root.table_id = table_id
        self.events.append(
            TableAssigned(self._root.id, table_id.value, datetime.now(timezone.utc))
        )

    def confirm(self) -> None:
        # Invariant: confirm only from CREATED
        if self._root.status != ReservationStatus.CREATED:
            raise ValueError("Invariant: only CREATED reservation can be confirmed")

        # Invariant: cannot confirm without table
        if self._root.table_id is None:
            raise ValueError("Invariant: cannot confirm without assigned table")

        self._root.status = ReservationStatus.CONFIRMED
        self.events.append(
            ReservationConfirmed(self._root.id, datetime.now(timezone.utc))
        )

    def cancel(self) -> None:
        # Invariant: cannot cancel COMPLETED
        if self._root.status == ReservationStatus.COMPLETED:
            raise ValueError("Invariant: cannot cancel COMPLETED reservation")

        # idempotent
        if self._root.status == ReservationStatus.CANCELLED:
            return

        self._root.status = ReservationStatus.CANCELLED
        self.events.append(
            ReservationCancelled(self._root.id, datetime.now(timezone.utc))
        )

    def mark_completed(self) -> None:
        # Invariant: can complete only CONFIRMED
        if self._root.status != ReservationStatus.CONFIRMED:
            raise ValueError("Invariant: can complete only CONFIRMED reservation")

        self._root.status = ReservationStatus.COMPLETED
