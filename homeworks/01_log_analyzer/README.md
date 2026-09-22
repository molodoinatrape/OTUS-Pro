# Анализатор nginx-логов

Выбирает последний лог по дате в имени, рассчитывает статистику запросов по URL и создаёт HTML-отчёт. Поддерживает обычные и gzip-файлы, JSON-конфигурацию и структурированное логирование.

## Запуск

Требуются Python 3.14 и Poetry. Для команд `make` нужен GNU Make.

Из корня репозитория:

```shell
cd homeworks/01_log_analyzer
poetry install
poetry run python log_analyzer.py --config config.logging.json
```

Тестовый лог берётся из `tests/sample`. Результат — `reports/report-2017.06.29.html`, журнал — `logs/analyzer.jsonl`. Для сортировки таблицы откройте HTML в браузере с доступом к интернету: jQuery загружается с внешнего сервера.

Все дальнейшие команды выполняются из каталога проекта, если не указано иное.

## Собственные логи и конфигурация

Поместите файлы в `logs`. Ожидаемый формат имени — `nginx-access-ui.log-YYYYMMDD[.gz]`. При совпадении дат выбирается несжатый файл. URL извлекается из поля запроса в кавычках, время обработки — из последнего поля строки.

```shell
poetry run python log_analyzer.py --config config.json
```

Без `--config` используется `config.json` из текущего рабочего каталога. Относительные пути внутри конфигурации также отсчитываются от рабочего каталога.

```json
{
  "LOG_DIR": "logs",
  "REPORT_DIR": "reports",
  "REPORT_SIZE": 10,
  "PARSE_ERROR_THRESHOLD": 0.5
}
```

| Параметр | Назначение | По умолчанию в коде |
|---|---|---|
| `LOG_DIR` | Каталог входных логов | `logs` |
| `REPORT_DIR` | Каталог отчётов | `reports` |
| `REPORT_SIZE` | Максимальное количество URL | `1000` |
| `PARSE_ERROR_THRESHOLD` | Допустимая доля неразобранных строк | `0.5` |
| `LOG_FILE` | Путь к JSONL-журналу | Вывод в терминал |

Значения JSON переопределяют настройки по умолчанию; в поставляемом `config.json` задан только `REPORT_SIZE = 10`. Пустой файл или `{}` оставляет настройки по умолчанию. Отсутствующий файл, неизвестные параметры и неверные типы значений приводят к ошибке. `REPORT_SIZE` должен быть положительным целым числом, порог — числом от 0 до 1; логические значения не принимаются.

Доля неразобранных строк проверяется после полного чтения. При строгом превышении порога новый отчёт не создаётся.

## Отчёт и ошибки

В отчёт попадают URL с наибольшим суммарным временем обработки. Для каждого URL выводятся количество и доля запросов, суммарное, среднее, максимальное и медианное время, а также доля общего времени. Время измеряется в секундах, доли — в процентах.

HTML и файл сортировки сохраняются в `REPORT_DIR`. Имя отчёта — `report-YYYY.MM.DD.html`. Готовый отчёт повторно не создаётся: для пересчёта удалите его или выберите другой каталог. HTML записывается через временный файл.

События записываются в JSON через structlog. При заданном `LOG_FILE` журнал дополняется; иначе сообщения выводятся в терминал.

| Код завершения | Значение |
|---|---|
| `0` | Успех, включая отсутствие подходящих логов или наличие готового отчёта |
| `1` | Ошибка обработки или прерывание через Ctrl+C |
| `2` | Ошибка аргументов командной строки |

## Сборка sdist и wheel

```shell
poetry check --lock
poetry build
```

В `dist` создаются:

- `otus_pro-0.1.0.tar.gz` — sdist;
- `otus_pro-0.1.0-py3-none-any.whl` — wheel.

Оба формата включают модуль анализатора и ресурсы HTML/JS. Сборка настроена в [pyproject.toml](pyproject.toml); готовые архивы исключены из Git.

### Установка wheel вне репозитория

Пример для PowerShell; выполнять в одном окне терминала после сборки:

```powershell
$wheelPath = (Resolve-Path "dist/otus_pro-0.1.0-py3-none-any.whl").Path
$wheelCheckDir = Join-Path ([System.IO.Path]::GetTempPath()) "log-analyzer-wheel-check"
poetry run python -m venv (Join-Path $wheelCheckDir ".venv")
Set-Location $wheelCheckDir
.\.venv\Scripts\python.exe -m pip install $wheelPath
.\.venv\Scripts\log-analyzer.exe --help
```

В этом рабочем каталоге создайте `logs`, поместите туда nginx-лог и сохраните `config.json` из примера выше. Затем запустите:

```powershell
.\.venv\Scripts\log-analyzer.exe --config config.json
$LASTEXITCODE
```

Отчёт появится в `reports`. Для запуска установленного пакета Poetry не требуется. После изменения исходников пересоберите wheel; для переустановки той же версии используйте `pip install --force-reinstall` через Python проверочного окружения.

## Docker Compose

Нужны Docker с Linux-контейнерами и Docker Compose. Из каталога проекта:

```shell
docker compose run --build --rm analyzer
```

| На компьютере | В контейнере | Доступ |
|---|---|---|
| `tests/sample` | `/data/logs` | Чтение |
| `config.docker.json` | `/config/config.json` | Чтение |
| `reports/docker` | `/data/reports` | Запись |

Результат — `reports/docker/report-2017.06.29.html`; он сохраняется после удаления контейнера. Для собственных логов измените подключение входного каталога в [compose.yaml](compose.yaml).

## Проверки

После `poetry install`, из каталога проекта:

```shell
make lint
make test
```

`make lint` запускает isort, Black, Flake8 и mypy. Дополнительные команды: `make format` — форматирование, `make coverage` — тесты с покрытием, `make run` — запуск с конфигурацией по умолчанию.

[GitHub Actions](../../.github/workflows/01-log-analyzer.yml) выполняет проверку Poetry, lint и pytest при `push` и `pull_request`. Сборка дистрибутивов проверяется отдельно командой `poetry build`.
