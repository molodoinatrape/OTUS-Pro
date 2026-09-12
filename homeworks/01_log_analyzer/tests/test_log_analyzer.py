import gzip
from datetime import date
from pathlib import Path

import pytest
from pytest import approx, raises

from log_analyzer import (
    LogFile,
    build_statistics,
    calculate_metrics,
    find_latest_log,
    group_endpoints,
    iter_logs,
    merge_config,
    parse_args,
    parse_line,
    process_log,
    read_config,
    to_report_rows,
    validate_overrides,
    write_report,
)

example_valid_line = (
    "1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "
    '"GET /api/v2/banner/25019354 HTTP/1.1" '
    '200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" '
    '"1498697422-2190034393-4708-9752759" "dc7161be3" 0.390'
)


def test_parse_line() -> None:
    output = ("/api/v2/banner/25019354", 0.39)
    result = parse_line(example_valid_line)

    assert result == output


def test_parse_line_empty() -> None:
    result = parse_line("")

    assert result is None


def test_parse_line_broken() -> None:
    result = parse_line("broken line")

    assert result is None


def test_parse_line_invalid_time() -> None:
    example_invalid_time = (
        "1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "
        '"GET /api/v2/banner/25019354 HTTP/1.1" '
        '200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" '
        '"1498697422-2190034393-4708-9752759" "dc7161be3" unknow'
    )
    example_negative_time = (
        "1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "
        '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" '
        '"Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" '
        '"1498697422-2190034393-4708-9752759" "dc7161be3" -0.5'
    )

    result_1 = parse_line(example_invalid_time)
    result_2 = parse_line(example_negative_time)

    assert result_1 is None
    assert result_2 is None


def test_parse_line_zero_time() -> None:
    example_zero_time = (
        "1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "
        '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" '
        '"Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" '
        '"1498697422-2190034393-4708-9752759" "dc7161be3" 0.00'
    )
    output = ("/api/v2/banner/25019354", 0.0)
    result_1 = parse_line(example_zero_time)

    assert result_1 == output


def test_group_endpoints() -> None:
    example_logs = [
        ("/catalog", 0.2),
        ("/search", 1.5),
        ("/catalog", 0.6),
    ]
    output_logs = {
        "/catalog": [0.2, 0.6],
        "/search": [1.5],
    }

    assert group_endpoints(example_logs) == output_logs


def test_group_endpoints_empty() -> None:
    example_logs = []

    assert group_endpoints(example_logs) == {}


def test_calculate_metrics() -> None:
    example_time_1 = [0.9, 0.1, 0.2]
    example_time_2 = [0.2, 0.6]
    example_time_3 = [0.0]

    assert calculate_metrics(example_time_1) == {
        "count": 3,
        "time_sum": 1.2,
        "time_avg": approx(0.4),
        "time_max": 0.9,
        "time_med": 0.2,
    }
    assert calculate_metrics(example_time_2) == {
        "count": 2,
        "time_sum": 0.8,
        "time_avg": approx(0.4),
        "time_max": 0.6,
        "time_med": 0.4,
    }
    assert calculate_metrics(example_time_3) == {
        "count": 1,
        "time_sum": 0.0,
        "time_avg": 0.0,
        "time_max": 0.0,
        "time_med": 0.0,
    }
    with raises(ValueError):
        calculate_metrics([])


def test_build_statistics() -> None:
    endpoints = {
        "/catalog": [0.2, 0.6],
        "/search": [1.2],
    }

    result = build_statistics(endpoints)

    assert list(result) == [
        "/search",
        "/catalog",
    ]

    assert result["/catalog"] == {
        "count": 2,
        "time_sum": 0.8,
        "time_avg": 0.4,
        "time_max": 0.6,
        "time_med": 0.4,
        "count_perc": 66.66666666666666,
        "time_perc": 40.0,
    }


def test_build_statistics_report_size() -> None:
    endpoints = {
        "/catalog": [0.2, 0.6],
        "/search": [1.2],
    }

    result = build_statistics(endpoints, report_size=1)

    assert result == {
        "/search": {
            "count": 1,
            "time_sum": 1.2,
            "time_avg": 1.2,
            "time_max": 1.2,
            "time_med": 1.2,
            "count_perc": 33.33333333333333,
            "time_perc": 60.0,
        }
    }


def test_build_statistics_empty() -> None:
    assert build_statistics({}) == {}

    assert build_statistics({"/catalog": [0.0], "/search": [0.0]}) == {
        "/catalog": {
            "count": 1,
            "time_sum": 0.0,
            "time_avg": 0.0,
            "time_max": 0.0,
            "time_med": 0.0,
            "count_perc": 50.0,
            "time_perc": 0.0,
        },
        "/search": {
            "count": 1,
            "time_sum": 0.0,
            "time_avg": 0.0,
            "time_max": 0.0,
            "time_med": 0.0,
            "count_perc": 50.0,
            "time_perc": 0.0,
        },
    }
    for report_size in (0, -1):
        with raises(ValueError):
            build_statistics({}, report_size=report_size)


def test_find_latest_log(tmp_path: Path) -> None:
    (tmp_path / "nginx-access-ui.log-20170630").touch()
    (tmp_path / "nginx-access-ui.log-20170702.gz").touch()
    (tmp_path / "nginx-access-ui.log-20170701").touch()

    assert find_latest_log(tmp_path) == LogFile(
        path=tmp_path / "nginx-access-ui.log-20170702.gz",
        log_date=date(2017, 7, 2),
        is_gzip=True,
    )


def test_find_latest_log_empty(tmp_path: Path) -> None:
    assert find_latest_log(tmp_path) is None


def test_find_latest_log_ignores_invalid(tmp_path: Path) -> None:
    (tmp_path / "nginx-access-ui.log-20170630").touch()
    (tmp_path / "nginx-access-ui.log-20990101.bz2").touch()
    (tmp_path / "nginx_access_ui.log_20990101.gz").touch()
    (tmp_path / "nginx-access-ui.log-20230229").touch()
    (tmp_path / "nginx-access-ui.log-20990102").mkdir()

    assert find_latest_log(tmp_path) == LogFile(
        path=tmp_path / "nginx-access-ui.log-20170630",
        log_date=date(2017, 6, 30),
        is_gzip=False,
    )


def test_iter_logs(tmp_path: Path) -> None:
    content = example_valid_line + "\nbroken line\n"
    (tmp_path / "sample.log").touch()
    (tmp_path / "sample.log.gz").touch()

    plain_path = tmp_path / "sample.log"
    gzip_path = tmp_path / "sample.log.gz"

    plain_path.write_text(content, encoding="utf-8")

    with gzip.open(gzip_path, "wt", encoding="utf-8") as file:
        file.write(content)

    plain_log = LogFile(
        path=plain_path,
        log_date=date(2017, 6, 29),
        is_gzip=False,
    )

    gzip_log = LogFile(
        path=gzip_path,
        log_date=date(2017, 6, 29),
        is_gzip=True,
    )

    expected = [("/api/v2/banner/25019354", 0.39)]

    assert list(iter_logs(plain_log)) == expected
    assert list(iter_logs(gzip_log)) == expected


def test_merge_config() -> None:
    defaults = {
        "LOG_DIR": "homeworks/01_log_analyzer/tests/fixtures",
        "REPORT_DIR": "reports",
        "REPORT_SIZE": 1000,
    }

    overrides = {"REPORT_SIZE": 10}

    merged = merge_config(defaults, overrides)

    assert merged == {
        "LOG_DIR": "homeworks/01_log_analyzer/tests/fixtures",
        "REPORT_DIR": "reports",
        "REPORT_SIZE": 10,
    }

    assert defaults == {
        "LOG_DIR": "homeworks/01_log_analyzer/tests/fixtures",
        "REPORT_DIR": "reports",
        "REPORT_SIZE": 1000,
    }

    assert overrides == {"REPORT_SIZE": 10}

    assert merged is not defaults

    empty_result = merge_config(defaults, {})

    assert empty_result == defaults
    assert empty_result is not defaults


def test_read_config(tmp_path: Path) -> None:
    (tmp_path / "sample.json").touch()
    (tmp_path / "empty.json").touch()
    (tmp_path / "invalid.json").touch()

    path = tmp_path / "sample.json"
    empty_path = tmp_path / "empty.json"
    invalid_path = tmp_path / "invalid.json"

    path.write_text('{"REPORT_SIZE": 10}', encoding="utf-8")
    empty_path.write_text("  ", encoding="utf-8")
    invalid_path.write_text("[1, 2]", encoding="utf-8")

    assert read_config(path) == {"REPORT_SIZE": 10}

    assert read_config(empty_path) == {}

    with raises(ValueError):
        read_config(invalid_path)


def test_validate_config() -> None:
    data = {
        "LOG_DIR": "homeworks/01_log_analyzer/tests/fixtures",
        "REPORT_DIR": "test",
        "REPORT_SIZE": 10,
    }

    assert validate_overrides({}) == {}
    assert validate_overrides(data) == data
    assert validate_overrides(data) is not data

    for error_value in ("10", 0, True):
        with pytest.raises(ValueError):
            validate_overrides({"REPORT_SIZE": error_value})

    with pytest.raises(ValueError):
        validate_overrides({"LOG_DIR": "  "})

    with pytest.raises(ValueError):
        validate_overrides({"REPORT_SIZE": 10, "UNKNOWN": 1})


def test_parse_args_default() -> None:
    args = parse_args([])
    expected = Path(__file__).resolve().parent.parent / "config.json"

    assert args.config == expected


def test_parse_args_custom() -> None:
    args = parse_args(["--config", "custom.json"])

    assert args.config == Path("custom.json")


def test_to_report_rows() -> None:
    statistics = {
        "/search": {"count": 1, "time_sum": 1.5},
        "/catalog": {"count": 2, "time_sum": 0.8},
    }

    assert to_report_rows(statistics) == [
        {"url": "/search", "count": 1, "time_sum": 1.5},
        {"url": "/catalog", "count": 2, "time_sum": 0.8},
    ]


def test_write_report(tmp_path: Path) -> None:
    script_path = tmp_path / "jquery.tablesorter.min.js"
    script_path.write_text("// test script", encoding="utf-8")

    report_path = write_report(
        tmp_path / "reports",
        date(2017, 6, 30),
        "<html>Тест</html>",
        script_path=script_path,
    )

    assert report_path == tmp_path / "reports" / "report-2017.06.30.html"

    copied_script = tmp_path / "reports" / "jquery.tablesorter.min.js"
    assert copied_script.read_text(encoding="utf-8") == "// test script"

    report = report_path.read_text(encoding="utf-8")
    assert report == "<html>Тест</html>"


def test_process_log(tmp_path: Path) -> None:
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "nginx-access-ui.log-20170630").touch()
    (tmp_path / "template").touch()

    logs_path = tmp_path / "logs"
    log = tmp_path / "logs" / "nginx-access-ui.log-20170630"
    template_path = tmp_path / "template"

    log.write_text(example_valid_line, encoding="utf-8")
    template_path.write_text(
        "<script>var table = $table_json;</script>", encoding="utf-8"
    )

    script_path = template_path.with_name("jquery.tablesorter.min.js")
    script_path.write_text("// test script", encoding="utf-8")

    report_path = process_log(
        log_dir=logs_path,
        report_dir=tmp_path / "reports",
        report_size=10,
        template_path=template_path,
    )

    report = report_path.read_text(encoding="utf-8")

    assert report.startswith("<script>var table =")
    assert report.endswith(";</script>")
    assert report_path == tmp_path / "reports" / "report-2017.06.30.html"
    assert report_path is not None
