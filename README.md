# OTUS-Pro

Домашние задания курса OTUS «Python-разработчик. Продвинутый уровень».

| Тема | Проект |
|---|---|
| 01. Анализ логов | [Анализатор nginx-логов](homeworks/01_log_analyzer/README.md): статистика URL, HTML-отчёт, тесты |
| 02. Дистрибуция и развёртывание | [Сборка sdist и wheel](homeworks/01_log_analyzer/README.md), установка пакета и Docker Compose на примере анализатора |
| 03. Аннотации типов | [Python Type Challenges](homeworks/03_type_annotation/README.md): Basic и Intermediate, проверка Pyright в Docker |
| 06. ООП | [Scoring API](homeworks/06_08_API_scoring/README.md): валидация запросов, авторизация, скоринг, интересы клиентов и тесты |
| 08. Тестирование | [Scoring API](homeworks/06_08_API_scoring/README.md): модульные и функциональные тесты, Redis, кеш, таймауты и повторы |
| 10. SOLID | [Практика SOLID](homeworks/10_11_SOLID_DDD_Clean_Architecture/SOLID/): обработка заказа, правила скидок, сохранение и уведомления |
| 11. DDD и чистая архитектура | [Бронирование столов](homeworks/10_11_SOLID_DDD_Clean_Architecture/project/README.md): создание и отмена брони, каталог столов, конфликты по времени и Unit of Work |

Инструкции запуска и требования находятся в README каждого проекта.

## Scoring API: два ДЗ в одном проекте

ДЗ 06 и 08 объединены в проекте `homeworks/06_08_API_scoring`.
Все проекты репозитория разрабатываются в общей ветке `main`.

- ДЗ 06: поля, валидация, авторизация и обработчики API.
- ДЗ 08: тесты, Redis, кеш, таймауты и повторные попытки.

У проекта один набор исходников, тестов и зависимостей. Условия заданий
сохранены отдельно: [ДЗ 06](homeworks/06_08_API_scoring/docs/06_task.md)
и [ДЗ 08](homeworks/06_08_API_scoring/docs/08_task.md).
Исходное решение ДЗ 06 остаётся в истории Git.

## SOLID и DDD

Материалы тем 10 и 11 находятся в `homeworks/10_11_SOLID_DDD_Clean_Architecture`.

- `SOLID` - отдельные примеры принципов SOLID на обработке заказа.
- `project` - доработанный пример бронирования столов из занятия по DDD.

В проекте бронирования добавлены модель и репозиторий столов, отмена брони,
проверка пересечений по времени и общий откат двух репозиториев.
Хранение реализовано в памяти, SQL и HTTP оставлены заготовками.
Окружение, запуск тестов и ограничения описаны в [README проекта](homeworks/10_11_SOLID_DDD_Clean_Architecture/project/README.md).

## CI

Проверки запускаются при `push` и `pull_request`:

- [Анализатор логов](.github/workflows/01-log-analyzer.yml): проверка Poetry, lint и pytest.
- [Аннотации типов](.github/workflows/03-type-annotation.yml): сборка Docker-образа и `make typing`.

Для проекта DDD отдельный workflow пока не настроен, тесты запускаются локально.
