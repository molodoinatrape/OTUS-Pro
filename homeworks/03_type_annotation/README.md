# Аннотации типов

Решения заданий [Python Type Challenges](https://github.com/laike9m/Python-Type-Challenges) в рамках курса OTUS Python Developer Professional.

## Структура

```text
03_type_annotation/
├── Dockerfile
├── docker_compose.yaml
├── Makefile
├── pyrightconfig.json
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

## Проверка через Make и Docker

Требуются GNU Make, Docker и Docker Compose. Команды выполнять из `homeworks/03_type_annotation`. На Windows Docker Desktop должен быть запущен, а движок Linux-контейнеров готов к работе.

Перед первой проверкой собрать образ:

```shell
docker compose -p otus-types -f docker_compose.yaml build otus-python-pro-homework2
```

Запустить проверку:

```shell
make typing
```

Make вызывает следующую команду:

```shell
docker compose -p otus-types -f docker_compose.yaml run --rm otus-python-pro-homework2 pyright --project /workspace/pyrightconfig.json
```

`otus-python-pro-homework2` — имя сервиса в Compose, а не номер проверяемого задания. `-p otus-types` задаёт имя Compose-проекта, `-f` выбирает файл Compose. `run` создаёт контейнер для выполнения Pyright вместо запуска сайта; `--rm` удаляет этот контейнер после завершения. Образ и файлы решений сохраняются. Для проверки запуск веб-сервера не требуется.

Каталог задания подключён как `.:/workspace:ro`: контейнер видит конфигурацию и актуальные решения с компьютера, но не может изменять их через это подключение. После редактирования решений или конфигурации достаточно повторить `make typing`; после изменения Dockerfile нужно пересобрать образ.

Pyright установлен внутри образа. Параметр `--project` указывает общую конфигурацию. `include` выбирает `solutions/01_basic` и `solutions/02_intermediate`: 12 файлов Basic и 16 файлов Intermediate. Advanced и Extreme в проверку не входят.

В Basic и Intermediate ожидаемые ошибки отмечены комментариями `# pyright: ignore[категория]`. Настройка `reportUnnecessaryTypeIgnoreComment: "error"` делает ненужное подавление ошибкой: если отрицательный пример становится допустимым, проверка должна упасть. Для отдельных составных примеров Intermediate используется `# pyright: ignore` без категории: он требует наличия диагностики на строке, но не проверяет её конкретную категорию. После получения вывода анализатора такие маркеры можно уточнить. Обычный маркер `# expect-type-error` сам Pyright не обрабатывает.

### Подтверждённый результат

Локальный запуск `make typing` для всех файлов Basic и Intermediate завершился с `0 errors, 0 warnings, 0 informations`.

| Уровень | Задание | Файл | Результат локальной проверки |
|---|---|---|------------------------------|
| Basic | any | [any.py](solutions/01_basic/any.py) | Пройдено                     |
| Basic | dict | [dict.py](solutions/01_basic/dict.py) | Пройдено                     |
| Basic | final | [final.py](solutions/01_basic/final.py) | Пройдено                     |
| Basic | kwargs | [kwargs.py](solutions/01_basic/kwargs.py) | Пройдено                     |
| Basic | list | [list.py](solutions/01_basic/list.py) | Пройдено                     |
| Basic | optional | [optional.py](solutions/01_basic/optional.py) | Пройдено                     |
| Basic | parameter | [parameter.py](solutions/01_basic/parameter.py) | Пройдено                     |
| Basic | return | [return.py](solutions/01_basic/return.py) | Пройдено                     |
| Basic | tuple | [tuple.py](solutions/01_basic/tuple.py) | Пройдено                     |
| Basic | typealias | [typealias.py](solutions/01_basic/typealias.py) | Пройдено                     |
| Basic | union | [union.py](solutions/01_basic/union.py) | Пройдено                     |
| Basic | variable | [variable.py](solutions/01_basic/variable.py) | Пройдено                     |
| Intermediate | await | [await.py](solutions/02_intermediate/await.py) | Пройдено                     |
| Intermediate | callable | [callable.py](solutions/02_intermediate/callable.py) | Пройдено                     |
| Intermediate | class_var | [class_var.py](solutions/02_intermediate/class_var.py) | Пройдено                     |
| Intermediate | decorator | [decorator.py](solutions/02_intermediate/decorator.py) | Пройдено                     |
| Intermediate | empty_tuple | [empty_tuple.py](solutions/02_intermediate/empty_tuple.py) | Пройдено                     |
| Intermediate | generic | [generic.py](solutions/02_intermediate/generic.py) | Пройдено                     |
| Intermediate | generic2 | [generic2.py](solutions/02_intermediate/generic2.py) | Пройдено                     |
| Intermediate | generic3 | [generic3.py](solutions/02_intermediate/generic3.py) | Пройдено                     |
| Intermediate | instance_var | [instance_var.py](solutions/02_intermediate/instance_var.py) | Пройдено                     |
| Intermediate | literal | [literal.py](solutions/02_intermediate/literal.py) | Пройдено                     |
| Intermediate | literalstring | [literalstring.py](solutions/02_intermediate/literalstring.py) | Пройдено                     |
| Intermediate | self | [self.py](solutions/02_intermediate/self.py) | Пройдено                     |
| Intermediate | typed_dict | [typed_dict.py](solutions/02_intermediate/typed_dict.py) | Пройдено                     |
| Intermediate | typed_dict2 | [typed_dict2.py](solutions/02_intermediate/typed_dict2.py) | Пройдено                     |
| Intermediate | typed_dict3 | [typed_dict3.py](solutions/02_intermediate/typed_dict3.py) | Пройдено                     |
| Intermediate | unpack | [unpack.py](solutions/02_intermediate/unpack.py) | Пройдено                     |

## GitHub Actions

Workflow [03-type-annotation.yml](../../.github/workflows/03-type-annotation.yml) запускается при `push` и `pull_request` на `ubuntu-latest`. Он получает код через `actions/checkout@v7`, собирает образ Compose и выполняет `make typing` из каталога задания. Проверяемые файлы и правила задаёт тот же `pyrightconfig.json`, что используется локально.

Для запуска CI нужно сохранить изменения в коммите и отправить их на GitHub. Результат смотреть во вкладке **Actions → Проверка аннотаций типов**, затем открыть задание `checks` и шаги сборки и типизации. Ненулевой код завершения проверки делает шаг неуспешным. Успешный запуск этого workflow на GitHub пока не подтверждён.

Образ собирается с клонированием тренажёра и установкой зависимостей из сети; его внешние версии пока не зафиксированы полностью. Поэтому локальная проверка и новая сборка CI могут использовать разные версии Pyright и зависимостей.
