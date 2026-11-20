from __future__ import annotations

from datetime import datetime, timedelta
from ipaddress import ip_address
import random
import string

import pytest

from app.algorithms.log_parser import LogParser
from app.models.event import Event, MalformedRecord


BASE = datetime(2026, 1, 1, 12, 0, 0)
V4 = ("192.0.2.10", "198.51.100.23", "203.0.113.7")
V6 = ("2001:db8::1", "2001:0db8:0:0:0:0:0:2", "2001:DB8::2")


def _valid_line(
    timestamp: datetime,
    outcome: str,
    username: str,
    source_ip: str,
    *,
    invalid_user: bool,
    pid: int,
    port: int,
) -> str:
    action = "Failed" if outcome == "FAILED" else "Accepted"
    user_part = f"invalid user {username}" if invalid_user else username
    return (
        f"{timestamp.isoformat()} sshd[{pid}]: {action} password for "
        f"{user_part} from {source_ip} port {port}"
    )


def _random_text(rng: random.Random) -> str:
    choices = [
        "",
        "   \t\n",
        "x" * rng.randint(1000, 3000),
        "🙂\u2603\u03bb\u4e2d" * rng.randint(1, 8),
        "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 120))),
    ]
    return rng.choice(choices)


@pytest.mark.parametrize("seed", range(50))
def test_random_strings_never_raise_and_preserve_malformed_input(seed: int) -> None:
    rng = random.Random(seed)
    parser = LogParser()
    valid = _valid_line(
        BASE,
        "FAILED",
        "admin",
        "203.0.113.7",
        invalid_user=False,
        pid=1,
        port=22,
    )
    cases = [
        _random_text(rng) for _ in range(500)
    ] + [
        valid[:index] for index in range(0, len(valid), max(1, len(valid) // 8))
    ] + [
        valid.replace("203.0.113.7", "999.1.1.1"),
        valid.replace("2026-01-01T12:00:00", "yesterday"),
        valid.replace("password", "pass"),
    ]

    for line_no, raw_line in enumerate(cases, start=1):
        result = parser.parse_line(raw_line, line_no)
        assert isinstance(result, (Event, MalformedRecord))
        if isinstance(result, MalformedRecord):
            assert result.line_no == line_no
            assert result.line_raw == raw_line


@pytest.mark.parametrize("seed", range(50))
def test_generated_valid_lines_round_trip(seed: int) -> None:
    rng = random.Random(seed)
    parser = LogParser()
    for index in range(24):
        timestamp = BASE + timedelta(seconds=rng.randint(0, 10_000))
        outcome = rng.choice(("FAILED", "SUCCESS"))
        username = f"user_{seed}_{index}"
        source_ip = rng.choice(V4 + V6)
        line = _valid_line(
            timestamp,
            outcome,
            username,
            source_ip,
            invalid_user=rng.choice((True, False)),
            pid=rng.randint(1, 99999),
            port=rng.randint(1, 65535),
        )

        result = parser.parse_line(line, index + 1)

        assert isinstance(result, Event)
        assert result.timestamp == timestamp
        assert result.username == username
        assert result.outcome == outcome
        assert result.source_ip == str(ip_address(source_ip))


@pytest.mark.parametrize("seed", range(50))
def test_corruption_classes_have_specific_reasons(seed: int) -> None:
    parser = LogParser()
    timestamp = BASE + timedelta(seconds=seed)
    valid = _valid_line(
        timestamp,
        "FAILED",
        "admin",
        "203.0.113.7",
        invalid_user=False,
        pid=seed + 1,
        port=22,
    )
    cases = (
        (valid.replace("203.0.113.7", "999.1.1.1"), "INVALID_IP"),
        (valid.replace(timestamp.isoformat(), "not-a-timestamp"), "BAD_TIMESTAMP"),
        (valid.replace(timestamp.isoformat(), timestamp.isoformat() + "+00:00"), "BAD_TIMESTAMP"),
        (valid.replace(timestamp.isoformat(), timestamp.isoformat() + "Z"), "BAD_TIMESTAMP"),
        (valid.replace("password", "pass"), "UNKNOWN_PATTERN"),
    )
    for line_no, (line, reason) in enumerate(cases, start=1):
        result = parser.parse_line(line, line_no)
        assert isinstance(result, MalformedRecord)
        assert result.reason == reason
        assert result.line_raw == line

