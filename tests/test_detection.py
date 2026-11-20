from dataclasses import replace
from datetime import datetime, timedelta
from time import perf_counter

import pytest

from app.algorithms.detection_engine import DetectionEngine
from app.algorithms.log_parser import LogParser
from app.models.event import Event
from app.utils.errors import ValidationError


BASE = datetime(2026, 10, 2, 8, 0, 0)


def event(
    event_id: int,
    seconds: int,
    *,
    source_ip: str = "203.0.113.7",
    outcome: str = "FAILED",
    line_no: int | None = None,
) -> Event:
    return Event(
        id=event_id,
        timestamp=BASE + timedelta(seconds=seconds),
        source_ip=source_ip,
        username="admin",
        outcome=outcome,
        file_id=None,
        line_no=event_id if line_no is None else line_no,
    )


def test_t01_three_valid_failures_do_not_reach_default_threshold() -> None:
    result = DetectionEngine().detect([event(1, 0), event(2, 60), event(3, 120)])

    assert result == []


def test_t03_exact_window_boundary_is_inclusive_and_one_second_over_is_not() -> None:
    at_boundary = [event(i + 1, seconds) for i, seconds in enumerate((0, 60, 120, 180, 600))]
    over_boundary = [event(i + 1, seconds) for i, seconds in enumerate((0, 60, 120, 180, 601))]

    boundary_result = DetectionEngine().detect(at_boundary)
    over_boundary_result = DetectionEngine().detect(over_boundary)

    assert len(boundary_result) == 1
    assert boundary_result[0].failure_count == 5
    assert over_boundary_result == []


def test_t04_worked_example_links_success_and_excludes_late_failure() -> None:
    events = [
        event(1, 10),
        event(2, 150),
        event(3, 240),
        event(4, 465),
        event(5, 595),
        event(6, 720, outcome="SUCCESS"),
        event(7, 900),
    ]

    result = DetectionEngine().detect(events)

    assert len(result) == 1
    incident = result[0]
    assert incident.source_ip == "203.0.113.7"
    assert incident.failure_count == 5
    assert incident.start_ts == BASE + timedelta(seconds=10)
    assert incident.end_ts == BASE + timedelta(seconds=595)
    assert incident.severity == "HIGH"
    assert incident.event_ids == [1, 2, 3, 4, 5, 6]
    assert 7 not in incident.event_ids


def test_t05_two_ips_are_isolated_and_near_miss_does_not_detect() -> None:
    events = [
        event(1, 0, source_ip="203.0.113.7"),
        event(2, 30, source_ip="198.51.100.23"),
        event(3, 60, source_ip="203.0.113.7"),
        event(4, 90, source_ip="198.51.100.23"),
        event(5, 120, source_ip="203.0.113.7"),
        event(6, 150, source_ip="198.51.100.23"),
        event(7, 180, source_ip="203.0.113.7"),
        event(8, 210, source_ip="198.51.100.23"),
        event(9, 240, source_ip="203.0.113.7"),
    ]

    result = DetectionEngine().detect(events)

    assert len(result) == 1
    assert result[0].source_ip == "203.0.113.7"
    assert result[0].failure_count == 5


def test_t06_detection_is_reproducible() -> None:
    events = [event(i + 1, i * 60) for i in range(5)]
    engine = DetectionEngine()

    assert engine.detect(events) == engine.detect(events)


def test_unsorted_events_are_sorted_without_mutating_input() -> None:
    events = [event(3, 120), event(1, 0), event(2, 60)]
    original = list(events)

    result = DetectionEngine().detect(events, threshold=3)

    assert events == original
    assert result[0].event_ids == [1, 2, 3]


def test_same_timestamp_uses_line_number_as_tie_breaker() -> None:
    events = [
        event(3, 0, line_no=3),
        event(1, 0, line_no=1),
        event(2, 0, line_no=2),
    ]

    result = DetectionEngine().detect(events, threshold=3)

    assert result[0].event_ids == [1, 2, 3]


def test_success_at_exact_window_boundary_sets_high_without_changing_count() -> None:
    events = [event(i + 1, i * 60) for i in range(5)]
    events.append(event(6, 4 * 60 + 600, outcome="SUCCESS"))

    result = DetectionEngine().detect(events)

    assert len(result) == 1
    assert result[0].severity == "HIGH"
    assert result[0].failure_count == 5
    assert result[0].event_ids[-1] == 6


def test_success_without_incident_does_not_create_one() -> None:
    result = DetectionEngine().detect([event(1, 0, outcome="SUCCESS")])

    assert result == []


def test_success_from_another_ip_does_not_affect_incident() -> None:
    events = [event(i + 1, i * 60) for i in range(5)]
    events.append(event(6, 360, source_ip="198.51.100.9", outcome="SUCCESS"))

    result = DetectionEngine().detect(events)

    assert result[0].severity == "MEDIUM"
    assert result[0].event_ids == [1, 2, 3, 4, 5]


def test_success_outside_window_does_not_affect_incident() -> None:
    events = [event(i + 1, i * 60) for i in range(5)]
    events.append(event(6, 1200, outcome="SUCCESS"))

    result = DetectionEngine().detect(events)

    assert result[0].severity == "MEDIUM"
    assert result[0].event_ids == [1, 2, 3, 4, 5]


def test_success_does_not_inflate_failure_count_when_later_failures_merge() -> None:
    events = [event(i + 1, i * 60) for i in range(5)]
    events.extend((event(6, 360, outcome="SUCCESS"), event(7, 420)))

    result = DetectionEngine().detect(events)

    assert result[0].failure_count == 6
    assert result[0].event_ids == [1, 2, 3, 4, 5, 6, 7]


def test_incident_merges_consecutive_detections_within_merge_window() -> None:
    events = [event(i + 1, i * 60) for i in range(5)]
    events.append(event(6, 360))

    result = DetectionEngine().detect(events)

    assert len(result) == 1
    assert result[0].failure_count == 6
    assert result[0].end_ts == BASE + timedelta(seconds=360)


def test_incident_reopens_after_merge_window() -> None:
    first = [event(i + 1, i * 60) for i in range(5)]
    second = [event(i + 6, 1800 + i * 60) for i in range(5)]

    result = DetectionEngine().detect(first + second)

    assert len(result) == 2
    assert [incident.event_ids for incident in result] == [
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10],
    ]


def test_all_failed_input_without_success_stays_medium() -> None:
    result = DetectionEngine().detect([event(i + 1, i) for i in range(10)])

    assert result[0].severity == "MEDIUM"


def test_empty_and_all_success_inputs_are_empty() -> None:
    engine = DetectionEngine()

    assert engine.detect([]) == []
    assert engine.detect([event(1, 0, outcome="SUCCESS") for _ in range(5)]) == []


def test_event_without_id_is_rejected() -> None:
    missing_id = event(1, 0)
    missing_id.id = None

    with pytest.raises(ValidationError):
        DetectionEngine().detect([missing_id])


@pytest.mark.parametrize("threshold", [2, 21, 5.0, True])
def test_invalid_threshold_is_rejected_before_events_are_consumed(threshold: object) -> None:
    class ExplodingIterable:
        def __iter__(self):
            raise AssertionError("events were consumed before parameter validation")

    with pytest.raises(ValidationError):
        DetectionEngine().detect(ExplodingIterable(), threshold=threshold)  # type: ignore[arg-type]


@pytest.mark.parametrize("window_minutes", [0, 61, 5.0, False])
def test_invalid_window_is_rejected(window_minutes: object) -> None:
    with pytest.raises(ValidationError):
        DetectionEngine().detect([], window_minutes=window_minutes)  # type: ignore[arg-type]


def test_threshold_and_window_range_endpoints_are_valid() -> None:
    assert DetectionEngine().detect([event(i + 1, i) for i in range(3)], threshold=3, window_minutes=1)
    assert DetectionEngine().detect([event(i + 1, i) for i in range(20)], threshold=20, window_minutes=60)


def test_mixed_ipv6_spellings_share_one_detection_window() -> None:
    lines = [
        "2026-10-02T08:00:00 sshd[1]: Failed password for admin from 2001:0db8:0:0:0:0:0:2 port 1",
        "2026-10-02T08:01:00 sshd[2]: Failed password for admin from 2001:DB8::2 port 2",
        "2026-10-02T08:02:00 sshd[3]: Failed password for admin from 2001:db8:0:0:0:0:0:2 port 3",
        "2026-10-02T08:03:00 sshd[4]: Failed password for admin from 2001:0DB8::2 port 4",
        "2026-10-02T08:04:00 sshd[5]: Failed password for admin from 2001:db8::2 port 5",
    ]
    parser = LogParser()
    events = [
        replace(parser.parse_line(line, line_no), id=line_no)
        for line_no, line in enumerate(lines, start=1)
    ]

    incidents = DetectionEngine().detect(events, threshold=5, window_minutes=10)

    assert len(incidents) == 1
    assert incidents[0].source_ip == "2001:db8::2"
    assert incidents[0].failure_count == 5
    assert incidents[0].event_ids == [1, 2, 3, 4, 5]


def test_large_single_ip_burst_merges_in_linear_time() -> None:
    events = [event(i + 1, i // 84) for i in range(50_000)]

    started = perf_counter()
    result = DetectionEngine().detect(events, threshold=5, window_minutes=10)
    elapsed = perf_counter() - started

    assert elapsed < 2
    assert len(result) == 1
    assert result[0].failure_count == 50_000


def test_failure_before_success_is_ordered_when_later_merge_links_it() -> None:
    events = [event(i + 1, i) for i in range(5)]
    events.append(event(6, 5))
    events.extend(
        (
            event(7, 15, line_no=7),
            event(8, 15, outcome="SUCCESS", line_no=8),
            event(9, 15, line_no=9),
            event(10, 15, line_no=10),
            event(11, 15, line_no=11),
        )
    )

    result = DetectionEngine().detect(events, threshold=5, window_minutes=10)

    assert len(result) == 1
    assert result[0].event_ids == list(range(1, 12))
    assert result[0].failure_count == 10
    assert result[0].severity == "HIGH"

