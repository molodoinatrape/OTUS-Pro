# Restaurant Booking (DDD + Clean Architecture)

Это учебный проект (bounded context **Booking**) для объяснения DDD и Clean Architecture на Python.

## Структура
- `src/booking/domain` — доменная модель (Entity/VO/Aggregate Root), инварианты, события, доменные сервисы, порты (Repository).
- `src/booking/application` — use-cases (handlers), Unit of Work порт.
- `src/booking/infrastructure` — адаптеры (in-memory repo/uow), заготовки под SQLAlchemy.
- `src/booking/entrypoints` — пример HTTP entrypoint (FastAPI-скелет без зависимости в pyproject).

## Быстрый старт (тесты)
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Доменные термины (Ubiquitous Language)
- Reservation — бронь
- TimeSlot — временной слот (start/end)
- PartySize — количество гостей
- TableId — идентификатор стола
- ReservationStatus — статус брони
