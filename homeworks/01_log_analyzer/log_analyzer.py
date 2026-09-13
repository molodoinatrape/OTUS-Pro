import argparse
import gzip
import json
import re
import shutil
from collections.abc import Generator, Iterable
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import median
from string import Template
from typing import TextIO

import structlog

config: dict[str, str | int] = {
    "LOG_DIR": "logs",
    "REPORT_DIR": "reports",
    "REPORT_SIZE": 1000,
}


@dataclass
class LogFile:
    path: Path
    log_date: date
    is_gzip: bool


def merge_config(
    defaults: dict[str, str | int],
    overrides: dict[str, str | int],
) -> dict[str, str | int]:
    new_config = defaults.copy()
    new_config.update(overrides)

    return new_config


def read_config(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")

    if text.strip() == "":
        return {}
    else:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        else:
            raise ValueError("Файл конфигурации должен быть словарём")


def validate_overrides(
    data: dict[str, object],
) -> dict[str, str | int]:
    valid_config: dict[str, str | int] = {}

    for key, value in data.items():
        if (
            key in ("LOG_DIR", "REPORT_DIR", "LOG_FILE")
            and isinstance(value, str)
            and value.strip() != ""
        ):
            valid_config[key] = value
        elif key == "REPORT_SIZE" and type(value) is int and value > 0:
            valid_config[key] = value
        else:
            raise ValueError(f"Недопустимое значение {key}")

    return valid_config


def parse_line(line: str) -> tuple[str, float] | None:
    """Извлечь URL и время запроса из строки лога"""
    try:
        url = line.split('"', maxsplit=2)[1].split()[1]
        request_time = float(line.rsplit(maxsplit=1)[-1])
    except IndexError, ValueError:
        return None

    if request_time < 0.0:
        return None

    log = url, request_time

    return log


def group_endpoints(logs: Iterable[tuple[str, float]]) -> dict[str, list[float]]:
    """Сгруппировать времена запросов по URL"""
    endpoints: dict[str, list[float]] = {}

    for url, request_time in logs:
        endpoints.setdefault(url, []).append(request_time)

    return endpoints


def calculate_metrics(times: list[float]) -> dict[str, int | float]:
    """Рассчитать количество, сумму, среднее, максимум и медиану времён запросов."""
    count = len(times)
    time_sum = sum(times)

    if count == 0:
        raise ValueError

    metrics: dict[str, int | float] = {
        "count": count,
        "time_sum": time_sum,
        "time_avg": time_sum / count,
        "time_max": max(times),
        "time_med": median(times),
    }

    return metrics


def build_statistics(
    endpoints: dict[str, list[float]],
    report_size: int = 1000,
) -> dict[str, dict[str, int | float]]:
    """Рассчитать статистику и выбрать URL с наибольшим суммарным временем."""

    total_request_time: float = 0.0
    total_requests: int = 0
    total_metrics: dict[str, dict[str, int | float]] = {}

    for url, times in endpoints.items():
        total_request_time += sum(times)
        total_requests += len(times)

        total_metrics[url] = calculate_metrics(times)

    for metrics in total_metrics.values():
        metrics["count_perc"] = metrics["count"] / total_requests * 100

        if total_request_time <= 0.0:
            metrics["time_perc"] = 0.0
        else:
            metrics["time_perc"] = metrics["time_sum"] / total_request_time * 100

    sorted_items = sorted(
        total_metrics.items(),
        key=lambda item: item[1]["time_sum"],
        reverse=True,
    )

    if report_size > 0:
        items = dict(sorted_items[:report_size])
    else:
        raise ValueError("report_size <= 0")

    return items


def find_latest_log(log_dir: Path) -> LogFile | None:
    """Найти самый свежий лог по дате в имени.

    Return:
        Описание найденного файла или None, если подходящих логов нет.
        При одинаковых датах предпочтение отдаётся несжатому файлу.
    """

    latest_path = None
    latest_date = None

    for path in log_dir.iterdir():
        match = re.fullmatch(
            r"nginx-access-ui\.log-([0-9]{8})(?:\.gz)?",
            path.name,
        )

        if path.is_file() and match:
            date_text = match.group(1)

            try:
                log_date = datetime.strptime(date_text, "%Y%m%d").date()
            except ValueError:
                continue

            if (
                (latest_date is None)
                or (log_date > latest_date)
                or (
                    log_date == latest_date
                    and latest_path is not None
                    and latest_path.suffix == ".gz"
                    and path.suffix != ".gz"
                )
            ):
                latest_path = path
                latest_date = log_date

    if latest_path is None or latest_date is None:
        return None

    return LogFile(
        path=latest_path, log_date=latest_date, is_gzip=(latest_path.suffix == ".gz")
    )


def iter_logs(log: LogFile) -> Generator[tuple[str, float], None, None]:
    if log.is_gzip:
        opener = gzip.open(log.path, "rt", encoding="utf-8")
    else:
        opener = open(log.path, "rt", encoding="utf-8")

    with opener as file:
        for line in file:
            result = parse_line(line)
            if result is not None:
                yield result


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().with_name("config.json"),
        help="Путь к конфигурации",
    )

    return parser.parse_args(argv)


def to_report_rows(
    statistics: dict[str, dict[str, int | float]],
) -> list[dict[str, str | int | float]]:
    report: list[dict[str, str | int | float]] = []

    for url, metrics in statistics.items():
        new_stats: dict[str, str | int | float] = {"url": url}

        new_stats.update(metrics)

        report.append(new_stats)

    return report


def render_report(
    template_path: Path,
    rows: list[dict[str, str | int | float]],
) -> str:
    template_text = template_path.read_text(encoding="utf-8")
    report_json = json.dumps(rows, ensure_ascii=False, allow_nan=False)
    table_json = report_json.replace("<", "\\u003c")

    html = Template(template_text).safe_substitute(table_json=table_json)

    return html


def write_report(
    report_dir: Path,
    log_date: date,
    html: str,
    script_path: Path,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / log_date.strftime("report-%Y.%m.%d.html")

    shutil.copyfile(
        script_path,
        report_dir / "jquery.tablesorter.min.js",
    )

    report_path.write_text(html, encoding="utf-8")

    return report_path


def process_log(
    log_dir: Path,
    report_dir: Path,
    report_size: int,
    template_path: Path,
) -> Path | None:
    """Основная обработка лога"""

    latest_log = find_latest_log(log_dir)

    if latest_log is None:
        return None

    with closing(iter_logs(latest_log)) as records:
        endpoints = group_endpoints(records)

    statistics = build_statistics(endpoints, report_size)

    rows = to_report_rows(statistics)

    report = render_report(template_path, rows)

    report_path = write_report(
        report_dir,
        log_date=latest_log.log_date,
        html=report,
        script_path=template_path.with_name("jquery.tablesorter.min.js"),
    )

    return report_path


def main(
    defaults: dict[str, str | int],
    argv: list[str] | None = None,
) -> int:
    setup_logging()
    logger = structlog.get_logger()

    args = parse_args(argv)

    stream: TextIO | None = None

    exit_code = 0

    try:
        overrides = read_config(args.config)
        validated_config = validate_overrides(overrides)

        final_config = merge_config(defaults=defaults, overrides=validated_config)

        log_file = final_config.get("LOG_FILE")

        if log_file is not None:
            if not isinstance(log_file, str):
                raise ValueError("LOG_FILE должен быть строкой")

            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            stream = log_path.open("a", encoding="utf-8")

            setup_logging(stream=stream)
            logger = structlog.get_logger()

        logger.info("Анализатор запущен")

        log_dir = final_config["LOG_DIR"]
        report_dir = final_config["REPORT_DIR"]
        report_size = final_config["REPORT_SIZE"]

        if not isinstance(log_dir, str):
            raise ValueError("LOG_DIR должен быть строкой")

        if not isinstance(report_dir, str):
            raise ValueError("REPORT_DIR должен быть строкой")

        if not isinstance(report_size, int) or isinstance(report_size, bool):
            raise ValueError("REPORT_SIZE должен быть целым числом")

        report_path = process_log(
            log_dir=Path(log_dir),
            report_dir=Path(report_dir),
            report_size=report_size,
            template_path=Path(__file__).resolve().parent / "templates" / "report.html",
        )

        if report_path is None:
            logger.info("Подходящих логов не найдено")
        else:
            logger.info("Отчёт создан", report_path=str(report_path))

    except (Exception, KeyboardInterrupt) as original_error:
        try:
            logger.error("Ошибка обработки", exc_info=original_error)
        except OSError:
            setup_logging()
            logger = structlog.get_logger()
            logger.error("Ошибка обработки", exc_info=original_error)

        exit_code = 1

    finally:
        if stream is not None:
            setup_logging()
            logger = structlog.get_logger()
            try:
                stream.close()
            except OSError:
                logger.error("Ошибка закрытия журнала", exc_info=True)
                exit_code = 1

    return exit_code


def setup_logging(stream: TextIO | None = None) -> None:
    """Логирование нашей программы"""

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=stream),
    )


if __name__ == "__main__":
    raise SystemExit(main(config))
