# Аннотации типов

Решения [Python Type Challenges](https://github.com/laike9m/Python-Type-Challenges): 12 заданий Basic и 16 Intermediate. Каждый файл содержит условие, решение и проверочные примеры.

## Проверка

Требуются Docker с Linux-контейнерами, Docker Compose и GNU Make. Python и Pyright устанавливаются внутри образа.

Из корня репозитория:

```shell
cd homeworks/03_type_annotation
docker compose -p otus-types -f docker_compose.yaml build otus-python-pro-homework2
make typing
```

Повторная проверка после изменения решений — `make typing`. Настройки и проверяемые каталоги заданы в [pyrightconfig.json](pyrightconfig.json). Advanced и Extreme в проверку не входят.

Отрицательные примеры отмечены `# pyright: ignore` с категорией ошибки или без неё. Настройка `reportUnnecessaryTypeIgnoreComment` требует, чтобы подавление было необходимо: если ошибка исчезнет, проверка завершится неуспешно. Файлы предназначены для статического анализа; запуск как обычных скриптов может завершиться исключением на отрицательном примере.

## Тренажёр

Из каталога проекта:

```shell
docker compose -p otus-types -f docker_compose.yaml up --build -d
```

Откройте [localhost:8001](http://localhost:8001). В редактор задания переносите решение с импортами; проверочные примеры тренажёр добавляет сам.

Остановка:

```shell
docker compose -p otus-types -f docker_compose.yaml stop
```

## Решения

| Уровень | Задание | Файл | Pyright |
|---|---|---|---|
| Basic | any | [any.py](solutions/01_basic/any.py) | Пройдено |
| Basic | dict | [dict.py](solutions/01_basic/dict.py) | Пройдено |
| Basic | final | [final.py](solutions/01_basic/final.py) | Пройдено |
| Basic | kwargs | [kwargs.py](solutions/01_basic/kwargs.py) | Пройдено |
| Basic | list | [list.py](solutions/01_basic/list.py) | Пройдено |
| Basic | optional | [optional.py](solutions/01_basic/optional.py) | Пройдено |
| Basic | parameter | [parameter.py](solutions/01_basic/parameter.py) | Пройдено |
| Basic | return | [return.py](solutions/01_basic/return.py) | Пройдено |
| Basic | tuple | [tuple.py](solutions/01_basic/tuple.py) | Пройдено |
| Basic | typealias | [typealias.py](solutions/01_basic/typealias.py) | Пройдено |
| Basic | union | [union.py](solutions/01_basic/union.py) | Пройдено |
| Basic | variable | [variable.py](solutions/01_basic/variable.py) | Пройдено |
| Intermediate | await | [await.py](solutions/02_intermediate/await.py) | Пройдено |
| Intermediate | callable | [callable.py](solutions/02_intermediate/callable.py) | Пройдено |
| Intermediate | class_var | [class_var.py](solutions/02_intermediate/class_var.py) | Пройдено |
| Intermediate | decorator | [decorator.py](solutions/02_intermediate/decorator.py) | Пройдено |
| Intermediate | empty_tuple | [empty_tuple.py](solutions/02_intermediate/empty_tuple.py) | Пройдено |
| Intermediate | generic | [generic.py](solutions/02_intermediate/generic.py) | Пройдено |
| Intermediate | generic2 | [generic2.py](solutions/02_intermediate/generic2.py) | Пройдено |
| Intermediate | generic3 | [generic3.py](solutions/02_intermediate/generic3.py) | Пройдено |
| Intermediate | instance_var | [instance_var.py](solutions/02_intermediate/instance_var.py) | Пройдено |
| Intermediate | literal | [literal.py](solutions/02_intermediate/literal.py) | Пройдено |
| Intermediate | literalstring | [literalstring.py](solutions/02_intermediate/literalstring.py) | Пройдено |
| Intermediate | self | [self.py](solutions/02_intermediate/self.py) | Пройдено |
| Intermediate | typed_dict | [typed_dict.py](solutions/02_intermediate/typed_dict.py) | Пройдено |
| Intermediate | typed_dict2 | [typed_dict2.py](solutions/02_intermediate/typed_dict2.py) | Пройдено |
| Intermediate | typed_dict3 | [typed_dict3.py](solutions/02_intermediate/typed_dict3.py) | Пройдено |
| Intermediate | unpack | [unpack.py](solutions/02_intermediate/unpack.py) | Пройдено |

## CI

[Workflow](../../.github/workflows/03-type-annotation.yml) при `push` и `pull_request` собирает Docker-образ и запускает `make typing` с той же конфигурацией, что используется локально.
