"""
Пример entrypoint (контроллер) под FastAPI.

Это скелет: FastAPI не добавлен в зависимости, чтобы проект оставался лёгким.
Для ДЗ можно поставить:
  pip install fastapi uvicorn

И подключить app.
"""

# from fastapi import FastAPI
# from pydantic import BaseModel
# from datetime import datetime
#
# from booking.application.commands import CreateReservation
# from booking.application.handlers import CreateReservationHandler
# from booking.domain.services import TableAllocationService
# from booking.infrastructure.uow import InMemoryUnitOfWork
#
# app = FastAPI()
#
# class CreateReservationDTO(BaseModel):
#     slot_start: datetime
#     duration_min: int
#     party_size: int
#
# @app.post("/reservations")
# def create_reservation(dto: CreateReservationDTO):
#     handler = CreateReservationHandler(InMemoryUnitOfWork(), TableAllocationService())
#     cmd = CreateReservation(**dto.dict())
#     # available_tables обычно берутся из Seating Context или read-model
#     reservation_id = handler(cmd, available_tables=[{"id": "T1", "capacity": 4}])
#     return {"reservation_id": reservation_id}
