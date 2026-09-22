# Аннотации типов

Решения заданий [Python Type Challenges](https://github.com/laike9m/Python-Type-Challenges) в рамках курса OTUS Python Developer Professional.

## Структура

```text
03_type_annotation/
├── Dockerfile
├── docker_compose.yaml
├── README.md
└── solutions/
    ├── 01_basic/          # 12 заданий
    └── 02_intermediate/   # 16 заданий
```

Каждое задание сохранено в отдельном Python-модуле с условием, решением и проверочными примерами.

| Уровень | Темы |
|---|---|
| [Basic](solutions/01_basic/) | Параметры и результат функций, коллекции, объединения типов, `None`, `Any`, `Final`, псевдонимы типов |
| [Intermediate](solutions/02_intermediate/) | `Awaitable`, `Callable`, декораторы, обобщённые функции, атрибуты классов и экземпляров, `Literal`, `LiteralString`, `Self`, `TypedDict`, именованные аргументы |

## Запуск тренажёра

Требуется Docker с Docker Compose и доступ к сети для первой сборки. На Windows запустить Docker Desktop и дождаться готовности движка.

Из корня репозитория перейти в каталог задания:

```shell
Set-Location homeworks/03_type_annotation
```

Собрать образ и запустить сервис в фоне:

```shell
docker compose -p otus-types -f docker_compose.yaml up --build -d
```

Открыть тренажёр: **http://localhost:8001/**.

Образ использует Python 3.14. Приложение запускается через Gunicorn; ответы в тренажёре проверяет Pyright. Node.js для Pyright устанавливается при сборке через `pyright[nodejs]`.

Повторный запуск с готовым образом:

```shell
docker compose -p otus-types -f docker_compose.yaml up -d
```

Проверить состояние и посмотреть последние сообщения сервера:

```shell
docker compose -p otus-types -f docker_compose.yaml ps
docker compose -p otus-types -f docker_compose.yaml logs --tail 50
```

Остановить сервис:

```shell
docker compose -p otus-types -f docker_compose.yaml stop
```

## Проверка решений

1. Открыть задание нужного уровня в тренажёре.
2. Перенести из соответствующего файла определение типов, функции или класса и необходимые импорты в редактор решения.
3. Выполнить проверку на странице задания. Проверочные вызовы из локального файла переносить в редактор решения не требуется: тренажёр добавляет свои проверки.

В файлах есть намеренно некорректные примеры, на которых анализатор должен обнаружить ошибки типов. Комментарий `# expect-type-error` обозначает ожидаемую диагностику в формате тренажёра. Обычный запуск Python не заменяет статическую проверку: часть функций оставлена учебными заглушками, а отрицательные примеры могут завершаться исключениями.
