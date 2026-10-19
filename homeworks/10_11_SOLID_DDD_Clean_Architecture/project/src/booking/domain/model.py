from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
# - даём наружу root только для чтения (property root)
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

    # ---------- Root доступен наружу только для чтения ----------
    @property
    def root(self) -> Reservation:
        return self._root

    # ---------- Factory-like constructor (удобно) ----------
    @classmethod
    def create(cls, reservation_id: str, slot: TimeSlot, party_size: PartySize) -> "ReservationAggregate":
        root = Reservation(reservation_id=reservation_id, slot=slot, party_size=party_size)
        agg = cls(root)
        agg.events.append(ReservationCreated(root.id, datetime.utcnow()))
        return agg

    # ---------- Operations (изменяют root и защищают инварианты) ----------

    def assign_table(self, table_id: TableId) -> None:
        # Invariant: assignment only when CREATED
        if self._root.status != ReservationStatus.CREATED:
            raise ValueError("Invariant: can assign table only for CREATED reservation")

        self._root.table_id = table_id
        self.events.append(TableAssigned(self._root.id, table_id.value, datetime.utcnow()))

    def confirm(self) -> None:
        # Invariant: confirm only from CREATED
        if self._root.status != ReservationStatus.CREATED:
            raise ValueError("Invariant: only CREATED reservation can be confirmed")

        # Invariant: cannot confirm without table
        if self._root.table_id is None:
            raise ValueError("Invariant: cannot confirm without assigned table")

        self._root.status = ReservationStatus.CONFIRMED
        self.events.append(ReservationConfirmed(self._root.id, datetime.utcnow()))

    def cancel(self) -> None:
        # Invariant: cannot cancel COMPLETED
        if self._root.status == ReservationStatus.COMPLETED:
            raise ValueError("Invariant: cannot cancel COMPLETED reservation")

        # idempotent
        if self._root.status == ReservationStatus.CANCELLED:
            return

        self._root.status = ReservationStatus.CANCELLED
        self.events.append(ReservationCancelled(self._root.id, datetime.utcnow()))

    def mark_completed(self) -> None:
        # Invariant: can complete only CONFIRMED
        if self._root.status != ReservationStatus.CONFIRMED:
            raise ValueError("Invariant: can complete only CONFIRMED reservation")

        self._root.status = ReservationStatus.COMPLETED
