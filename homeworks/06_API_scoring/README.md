# Scoring API

Учебный HTTP API с валидацией запросов. Два метода: `online_score` — расчёт
оценки, `clients_interests` — получение интересов клиентов.

Проверено на Python 3.14.3. Внешние зависимости не нужны.

## Запуск

Команды выполняются из папки `homeworks/06_API_scoring`.

```sh
python api.py
```

По умолчанию сервер слушает `localhost:8080`, логи выводятся в консоль.
Другой порт и запись логов в файл:

```sh
python api.py -p 8081 -l api.log
```

## Тесты

```sh
python -m unittest discover -s tests -p "test.py" -v
```

## Запросы

Оба метода вызываются через `POST /method` с заголовком
`Content-Type: application/json`. Готовые запросы находятся в
[requests.http](tests/requests.http), их можно запускать через HTTP Client в PyCharm.

Токен обычного пользователя: `SHA-512(account + login + SALT)` в виде
шестнадцатеричной строки. Если `account` отсутствует, используется пустая строка.
Для `login=user` без `account`:

```sh
python -c "import hashlib; print(hashlib.sha512(b'userOtus').hexdigest())"
```

Подставьте результат в поле `token`:

```json
{
  "login": "user",
  "token": "<токен>",
  "method": "online_score",
  "arguments": {"phone": "79991234567", "email": "user@example.com"}
}
```

Ответ: `{"response": {"score": 3.0}, "code": 200}`.

Для интересов клиентов замените `method` на `clients_interests`, а `arguments`
на `{"client_ids": [1, 2]}`. Пример ответа:

```json
{"response": {"1": ["books", "music"], "2": ["sport", "travel"]}, "code": 200}
```

Интересы выбираются случайно. Ошибки возвращаются в формате
`{"error": "<сообщение или словарь ошибок>", "code": 422}`.

Полное описание полей и правил — в [условии задания](docs/task.md).
