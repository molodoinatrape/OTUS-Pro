# OTUS-Pro

Домашние задания курса OTUS «Python-разработчик. Продвинутый уровень».

| Тема | Проект |
|---|---|
| 01. Анализ логов | [Анализатор nginx-логов](homeworks/01_log_analyzer/README.md): статистика URL, HTML-отчёт, тесты |
| 02. Дистрибуция и развёртывание | [Сборка sdist и wheel](homeworks/01_log_analyzer/README.md), установка пакета и Docker Compose на примере анализатора |
| 03. Аннотации типов | [Python Type Challenges](homeworks/03_type_annotation/README.md): Basic и Intermediate, проверка Pyright в Docker |

Инструкции запуска и требования находятся в README каждого проекта.

## CI

Проверки запускаются при `push` и `pull_request`:

- [Анализатор логов](.github/workflows/01-log-analyzer.yml): проверка Poetry, lint и pytest.
- [Аннотации типов](.github/workflows/03-type-annotation.yml): сборка Docker-образа и `make typing`.
