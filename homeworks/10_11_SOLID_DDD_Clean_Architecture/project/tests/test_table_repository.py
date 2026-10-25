from booking.domain.model import Table, TableId
from booking.infrastructure.repositories import InMemoryTableRepository


def test_table_repository_returns_none_for_unknown_id():
    repository = InMemoryTableRepository()

    assert repository.get(TableId("missing")) is None
    assert repository.list_all() == []


def test_table_repository_finds_table_by_identifier_value():
    repository = InMemoryTableRepository()
    table = Table(TableId("T1"), capacity=4)
    repository.add(table)

    # Новый экземпляр TableId с тем же значением должен найти сохранённый стол.
    saved = repository.get(TableId("T1"))

    assert saved is not None
    assert saved.id == TableId("T1")
    assert saved.capacity == 4


def test_table_repository_lists_all_tables():
    repository = InMemoryTableRepository()
    repository.add(Table(TableId("T1"), capacity=2))
    repository.add(Table(TableId("T2"), capacity=6))

    tables = repository.list_all()

    assert len(tables) == 2
    assert {table.id: table.capacity for table in tables} == {
        TableId("T1"): 2,
        TableId("T2"): 6,
    }
