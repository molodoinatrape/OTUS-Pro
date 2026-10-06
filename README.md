# OTUS-Pro

Домашние задания курса OTUS «Python-разработчик. Продвинутый уровень».

| Тема | Проект |
|---|---|
| 01. Анализ логов | [Анализатор nginx-логов](homeworks/01_log_analyzer/README.md): статистика URL, HTML-отчёт, тесты |
| 02. Дистрибуция и развёртывание | [Сборка sdist и wheel](homeworks/01_log_analyzer/README.md), установка пакета и Docker Compose на примере анализатора |
| 03. Аннотации типов | [Python Type Challenges](homeworks/03_type_annotation/README.md): Basic и Intermediate, проверка Pyright в Docker |
| 06. ООП | [Scoring API](homeworks/06_08_API_scoring/README.md): валидация запросов, авторизация, скоринг, интересы клиентов и тесты |
| 08. Тестирование | [Scoring API](homeworks/06_08_API_scoring/README.md): развитие ДЗ 06 — модульные тесты, параметризация, хранилище и кеш; в работе |

Инструкции запуска и требования находятся в README каждого проекта.

## Scoring API: два ДЗ в одном проекте

ДЗ 06 и 08 используют общий каталог `homeworks/06_08_API_scoring`.
Версии решения разделены ветками Git:

| Домашнее задание | Ветка | Содержание |
|---|---|---|
| 06. ООП — Scoring API | `hw06-API_scoring` | Базовая реализация API: поля, валидация, авторизация и обработчики |
| 08. Тестирование Scoring API | `hw08-testing` | Развитие API: модульные тесты, key-value хранилище, кеш, таймауты и повторные подключения |

Код предыдущего ДЗ сохраняется в ветке `hw06-API_scoring`, а изменения для
следующего выполняются в `hw08-testing` в том же каталоге. Копировать проект
в отдельную папку для ДЗ 08 не требуется.

## CI

Проверки запускаются при `push` и `pull_request`:

- [Анализатор логов](.github/workflows/01-log-analyzer.yml): проверка Poetry, lint и pytest.
- [Аннотации типов](.github/workflows/03-type-annotation.yml): сборка Docker-образа и `make typing`.
