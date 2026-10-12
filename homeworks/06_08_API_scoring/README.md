# Scoring API - ДЗ 06 и 08

Один проект для двух домашних заданий курса OTUS.

- ДЗ 06: поля запросов, валидация, авторизация и HTTP API.
- ДЗ 08: тесты, Redis, кеширование оценок, таймауты и повторные попытки.

Каталог проекта: `homeworks/06_08_API_scoring`.
Рабочая ветка: `main`, общая для всех проектов репозитория.
Исходное решение ДЗ 06 сохранено в истории Git.

Условия заданий: [ДЗ 06](docs/06_task.md) и [ДЗ 08](docs/08_task.md).

## Состояние

Реализованы проверки полей, авторизация, скоринг и Store. Добавлены тесты
хранилища, скоринга, обработчиков и HTTP. Store создаётся при запуске сервера
и передаётся через HTTP-обработчик в функции скоринга. Полный набор тестов:
205 passed. Проверки Flake8, Black и isort прошли для приложения и тестов.
Обычный запуск API с настоящим Redis проверен: оценка 3.0 и интересы клиентов
возвращаются с кодом 200, пустой запрос получает код 422.

## Окружение

Нужны Python 3.14, uv и Docker Desktop с Linux-контейнерами.
Команды выполняются из каталога проекта.

```powershell
uv sync
```

Зависимости описаны в pyproject.toml, точные версии закреплены в uv.lock.
Python-клиент redis установлен в окружении проекта; сервер Redis запускается
отдельно.

## Redis

Первый запуск контейнера:

```powershell
docker run -d --name otus-scoring-redis -p 127.0.0.1:6379:6379 redis:8
docker exec otus-scoring-redis redis-cli ping
```

Ожидаемый ответ - PONG. Для запуска уже созданного контейнера:

```powershell
docker start otus-scoring-redis
```

Оценки хранятся в кеше 3600 секунд. Интересы читаются из JSON по ключам
`i:<client_id>`. Примеры заданы в словаре INTERESTS файла seed_interests.py.
Для их записи в запущенный Redis:

```powershell
uv run python seed_interests.py
```

Если ключа интересов нет, API возвращает пустой список. При недоступности
хранилища интересов запрос завершается ошибкой. Недоступность кеша не мешает
вычислить оценку.

## Запуск API

Запуск сервера:

```powershell
uv run python api.py
uv run python api.py -p 8081 -l api.log
```

По умолчанию сервер слушает localhost:8080 и пишет логи в консоль.

## Тесты

Полный набор, включая прежние unittest-тесты:

```powershell
uv run pytest tests tests/test.py -v
```

Отдельный запуск прежних функциональных тестов:

```powershell
uv run python -m unittest discover -s tests -p "test.py" -v
```

Клиент Redis в тестах заменён Mock, запущенный Redis для них не нужен.
HTTP-тесты создают локальный сервер на свободном порту и закрывают его
после проверки.

Покрытие кода:

```powershell
uv run pytest tests tests/test.py --cov=api --cov=scoring --cov=store --cov-report=term-missing
```

Проверки стиля:

```powershell
uv run flake8 api.py scoring.py store.py seed_interests.py tests
uv run black --check api.py scoring.py store.py seed_interests.py tests
uv run python -X utf8 -m isort --check-only api.py scoring.py store.py seed_interests.py tests
```

## Запросы

Оба метода вызываются через POST /method с Content-Type: application/json.
Примеры находятся в [requests.http](tests/requests.http).

Токен обычного пользователя - SHA-512 от account + login + SALT.
Отсутствующий account считается пустой строкой. Для login=user без account:

```powershell
uv run python -c "import hashlib; print(hashlib.sha512(b'userOtus').hexdigest())"
```

Подставьте токен в запрос:

```json
{
  "login": "user",
  "token": "<токен>",
  "method": "online_score",
  "arguments": {"phone": "79990000000", "email": "user@example.com"}
}
```

Ожидаемый ответ: `{"response": {"score": 3.0}, "code": 200}`.

Для интересов используйте method=clients_interests и arguments с client_ids.
Если примеры выше записаны в Redis, для ID 1 и 2 ожидается:

```json
{"response": {"1": ["books", "music"], "2": ["sport", "travel"]}, "code": 200}
```
