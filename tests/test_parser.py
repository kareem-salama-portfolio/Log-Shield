from datetime import datetime

import pytest

from app.algorithms.log_parser import LogParser
from app.models.event import Event, MalformedRecord


def test_p01_valid_failed_log_becomes_failed_event() -> None:
    result = LogParser().parse_line(
        "2026-10-02T08:00:10 sshd[2211]: Failed password for admin "
        "from 203.0.113.7 port 52144",
        1,
    )

    assert isinstance(result, Event)
    assert result.timestamp == datetime(2026, 10, 2, 8, 0, 10)
    assert result.source_ip == "203.0.113.7"
    assert result.username == "admin"
    assert result.outcome == "FAILED"
    assert result.line_no == 1
    assert result.id is None
    assert result.file_id is None


def test_p02_valid_success_log_becomes_success_event() -> None:
    result = LogParser().parse_line(
        "2026-10-02T08:12:00 sshd[2290]: Accepted password for admin "
        "from 203.0.113.7 port 52201",
        2,
    )

    assert isinstance(result, Event)
    assert result.outcome == "SUCCESS"
    assert result.username == "admin"


def test_p03_invalid_ip_is_malformed_without_raising() -> None:
    result = LogParser().parse_line(
        "2026-10-02T09:00:00 sshd[2305]: Failed password for admin "
        "from 999.1.1.1 port 40022",
        3,
    )

    assert isinstance(result, MalformedRecord)
    assert result.reason == "INVALID_IP"
    assert result.line_no == 3


def test_p04_invalid_timestamp_is_malformed() -> None:
    result = LogParser().parse_line(
        "yesterday sshd[2305]: Failed password for admin "
        "from 198.51.100.23 port 40022",
        4,
    )

    assert isinstance(result, MalformedRecord)
    assert result.reason == "BAD_TIMESTAMP"


def test_p05_unknown_pattern_is_malformed() -> None:
    result = LogParser().parse_line("not an sshd authentication record", 5)

    assert isinstance(result, MalformedRecord)
    assert result.reason == "UNKNOWN_PATTERN"
    assert result.line_raw == "not an sshd authentication record"


def test_p06_invalid_user_syntax_extracts_username() -> None:
    result = LogParser().parse_line(
        "2026-10-02T09:00:00 sshd[2305]: Failed password for invalid user test "
        "from 198.51.100.23 port 40022",
        6,
    )

    assert isinstance(result, Event)
    assert result.username == "test"
    assert result.outcome == "FAILED"


def test_p07_ipv6_is_accepted() -> None:
    result = LogParser().parse_line(
        "2026-10-02T09:00:00 sshd[2305]: Accepted password for admin "
        "from 2001:db8::7 port 40022",
        7,
    )

    assert isinstance(result, Event)
    assert result.source_ip == "2001:db8::7"


def test_ip_addresses_are_canonicalized_without_changing_ipv4() -> None:
    parser = LogParser()
    expanded = parser.parse_line(
        "2026-10-02T09:00:00 sshd[2305]: Accepted password for admin "
        "from 2001:0db8:0:0:0:0:0:2 port 40022",
        8,
    )
    uppercase = parser.parse_line(
        "2026-10-02T09:00:01 sshd[2306]: Accepted password for admin "
        "from 2001:DB8::2 port 40023",
        9,
    )
    ipv4 = parser.parse_line(
        "2026-10-02T09:00:02 sshd[2307]: Accepted password for admin "
        "from 203.0.113.7 port 40024",
        10,
    )

    assert isinstance(expanded, Event)
    assert isinstance(uppercase, Event)
    assert isinstance(ipv4, Event)
    assert expanded.source_ip == "2001:db8::2"
    assert uppercase.source_ip == "2001:db8::2"
    assert ipv4.source_ip == "203.0.113.7"


def test_parser_keeps_valid_and_malformed_records_separate() -> None:
    events, malformed = LogParser().parse_lines(
        [
            "2026-10-02T08:00:10 sshd[2211]: Failed password for admin "
            "from 203.0.113.7 port 52144",
            "bad record",
        ]
    )

    assert len(events) == 1
    assert len(malformed) == 1
    assert malformed[0].line_no == 2


def test_t01_three_valid_lines_become_three_events() -> None:
    lines = [
        "2026-10-02T08:00:10 sshd[2211]: Failed password for admin "
        "from 203.0.113.7 port 52144",
        "2026-10-02T08:02:30 sshd[2290]: Accepted password for admin "
        "from 203.0.113.7 port 52201",
        "2026-10-02T08:04:00 sshd[2305]: Failed password for invalid user test "
        "from 198.51.100.23 port 40022",
    ]

    events, malformed = LogParser().parse_lines(lines)

    assert len(events) == 3
    assert malformed == []
    assert [
        (event.timestamp, event.source_ip, event.username, event.outcome, event.line_no)
        for event in events
    ] == [
        (datetime(2026, 10, 2, 8, 0, 10), "203.0.113.7", "admin", "FAILED", 1),
        (datetime(2026, 10, 2, 8, 2, 30), "203.0.113.7", "admin", "SUCCESS", 2),
        (datetime(2026, 10, 2, 8, 4), "198.51.100.23", "test", "FAILED", 3),
    ]


def test_sample_log_counts() -> None:
    lines = [
        "2026-10-02T08:00:10 sshd[1]: Failed password for admin from 203.0.113.7 port 1",
        "2026-10-02T08:01:10 sshd[2]: Accepted password for admin from 203.0.113.7 port 2",
        "2026-10-02T08:02:10 sshd[3]: Failed password for invalid user test from 198.51.100.23 port 3",
        "2026-10-02T08:03:10 sshd[4]: Failed password for admin from 192.0.2.10 port 4",
        "2026-10-02T08:04:10 sshd[5]: Accepted password for admin from 192.0.2.10 port 5",
        "2026-10-02T08:05:10 sshd[6]: Failed password for admin from 203.0.113.7 port 6",
        "2026-10-02T08:06:10 sshd[7]: Accepted password for admin from 198.51.100.23 port 7",
        "2026-10-02T08:07:10 sshd[8]: Failed password for admin from 999.1.1.1 port 8",
        "yesterday sshd[9]: Failed password for admin from 203.0.113.7 port 9",
        "not an sshd authentication record",
    ]

    events, malformed = LogParser().parse_lines(lines)

    assert len(events) == 7
    assert len(malformed) == 3
    assert [record.reason for record in malformed] == [
        "INVALID_IP",
        "BAD_TIMESTAMP",
        "UNKNOWN_PATTERN",
    ]


@pytest.mark.parametrize("timestamp", ["2026-10-02T08:00:10+00:00", "2026-10-02T08:00:10Z"])
def test_timezone_aware_timestamp_is_bad_timestamp(timestamp: str) -> None:
    raw_line = f"{timestamp} sshd[1]: Failed password for admin from 203.0.113.7 port 1"

    result = LogParser().parse_line(raw_line, 1)

    assert isinstance(result, MalformedRecord)
    assert result.line_raw == raw_line
    assert result.reason == "BAD_TIMESTAMP"

