# OTUS-Pro

Домашние задания курса OTUS «Python-разработчик. Продвинутый уровень».

| Тема | Проект |
|---|---|
| 01. Анализ логов | [Анализатор nginx-логов](homeworks/01_log_analyzer/README.md): статистика URL, HTML-отчёт, тесты |
| 02. Дистрибуция и развёртывание | [Сборка sdist и wheel](homeworks/01_log_analyzer/README.md), установка пакета и Docker Compose на примере анализатора |
| 03. Аннотации типов | [Python Type Challenges](homeworks/03_type_annotation/README.md): Basic и Intermediate, проверка Pyright в Docker |
| 06. ООП | [Scoring API](homeworks/06_08_API_scoring/README.md): валидация запросов, авторизация, скоринг, интересы клиентов и тесты |
| 08. Тестирование | [Scoring API](homeworks/06_08_API_scoring/README.md): модульные и функциональные тесты, Redis, кеш, таймауты и повторы |

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

## CI

Проверки запускаются при `push` и `pull_request`:

- [Анализатор логов](.github/workflows/01-log-analyzer.yml): проверка Poetry, lint и pytest.
- [Аннотации типов](.github/workflows/03-type-annotation.yml): сборка Docker-образа и `make typing`.
