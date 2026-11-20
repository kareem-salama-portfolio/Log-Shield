from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import random

import pytest

from app.algorithms.detection_engine import DetectionEngine
from app.models.event import Event
from app.models.incident import Incident


BASE = datetime(2026, 1, 1)
IP_POOL = (
    "192.0.2.10",
    "198.51.100.23",
    "2001:db8::1",
    "2001:0db8:0:0:0:0:0:2",
)


def _reference_detect(
    events: list[Event],
    threshold: int,
    window_minutes: int,
) -> list[Incident]:
    """A deliberately direct reference implementation of the written rules."""

    ordered = sorted(events, key=lambda item: (item.timestamp, item.line_no))
    window = timedelta(minutes=window_minutes)
    windows: dict[str, list[Event]] = {}
    open_incidents: dict[str, Incident] = {}
    evidence: dict[int, list[Event]] = {}
    linked_failures: dict[int, set[int]] = {}
    incidents: list[Incident] = []

    for event in ordered:
        if event.outcome == "SUCCESS":
            incident = open_incidents.get(event.source_ip)
            if incident is not None:
                elapsed = event.timestamp - incident.end_ts
                if timedelta(0) <= elapsed <= window:
                    incident.severity = "HIGH"
                    evidence[id(incident)].append(event)
            continue

        if event.outcome != "FAILED":
            continue

        current_window = windows.setdefault(event.source_ip, [])
        current_window.append(event)
        while (
            current_window
            and event.timestamp - current_window[0].timestamp > window
        ):
            current_window.pop(0)

        if len(current_window) < threshold:
            continue

        incident = open_incidents.get(event.source_ip)
        if incident is not None and incident.end_ts >= event.timestamp - window:
            incident_new_failures = [
                failure
                for failure in current_window
                if failure.id not in linked_failures[id(incident)]
            ]
            evidence[id(incident)].extend(incident_new_failures)
            linked_failures[id(incident)].update(
                failure.id for failure in incident_new_failures
            )
            incident.failure_count += len(incident_new_failures)
            incident.end_ts = event.timestamp
            continue

        incident = Incident(
            source_ip=event.source_ip,
            start_ts=current_window[0].timestamp,
            end_ts=event.timestamp,
            failure_count=len(current_window),
            event_ids=[],
        )
        incidents.append(incident)
        open_incidents[event.source_ip] = incident
        evidence[id(incident)] = list(current_window)
        linked_failures[id(incident)] = {
            failure.id for failure in current_window
        }

    for incident in incidents:
        incident.event_ids = [
            event.id
            for event in sorted(
                evidence[id(incident)],
                key=lambda item: (item.timestamp, item.line_no),
            )
        ]
    return incidents


def _make_events(seed: int) -> tuple[list[Event], int, int]:
    rng = random.Random(seed)
    window_minutes = rng.randint(1, 60)
    ip_count = rng.randint(1, 4)
    if ip_count == 1:
        ips = [rng.choice(IP_POOL)]
    else:
        ips = [rng.choice(IP_POOL[:2]), rng.choice(IP_POOL[2:])]
        remaining = [ip for ip in IP_POOL if ip not in ips]
        ips.extend(rng.sample(remaining, ip_count - 2))

    window_seconds = window_minutes * 60
    records: list[tuple[datetime, str, str]] = []
    primary = ips[0]
    for offset in (0, window_seconds, window_seconds + 1, window_seconds):
        records.append((BASE + timedelta(seconds=offset), primary, "FAILED"))

    for _ in range(116):
        ip = rng.choice(ips)
        offset = rng.choice(
            (
                rng.randint(0, window_seconds),
                rng.randint(0, window_seconds),
                rng.randint(max(0, window_seconds - 1), window_seconds + 1),
                rng.randint(window_seconds + 1, 3 * window_seconds + 1),
            )
        )
        outcome = "FAILED" if rng.random() < 0.68 else "SUCCESS"
        records.append((BASE + timedelta(seconds=offset), ip, outcome))

    line_numbers = list(range(1, len(records) + 1))
    rng.shuffle(line_numbers)
    events = [
        Event(
            id=index,
            timestamp=timestamp,
            source_ip=source_ip,
            username="user",
            outcome=outcome,
            file_id=None,
            line_no=line_numbers[index - 1],
        )
        for index, (timestamp, source_ip, outcome) in enumerate(records, start=1)
    ]
    rng.shuffle(events)
    return events, rng.randint(3, 20), window_minutes


def _assert_invariants(events: list[Event], incidents: list[Incident]) -> None:
    by_id = {event.id: event for event in events}
    for incident in incidents:
        assert incident.failure_count == sum(
            by_id[event_id].outcome == "FAILED"
            for event_id in incident.event_ids
        )
        assert len(incident.event_ids) == len(set(incident.event_ids))
        evidence = [by_id[event_id] for event_id in incident.event_ids]
        assert evidence == sorted(
            evidence,
            key=lambda event: (event.timestamp, event.line_no),
        )
        assert all(event.source_ip == incident.source_ip for event in evidence)
        success_ids = [event.id for event in evidence if event.outcome == "SUCCESS"]
        if incident.severity == "HIGH":
            assert success_ids
        else:
            assert not success_ids


@pytest.mark.parametrize("seed", range(50))
def test_random_detection_matches_reference_and_invariants(seed: int) -> None:
    events, threshold, window_minutes = _make_events(seed)
    original = list(events)
    engine = DetectionEngine()

    actual = engine.detect(events, threshold=threshold, window_minutes=window_minutes)
    expected = _reference_detect(
        events,
        threshold=threshold,
        window_minutes=window_minutes,
    )

    assert actual == expected
    assert events == original
    assert engine.detect(events, threshold=threshold, window_minutes=window_minutes) == actual
    shuffled = list(events)
    random.Random(seed + 20_000).shuffle(shuffled)
    assert engine.detect(shuffled, threshold=threshold, window_minutes=window_minutes) == actual
    _assert_invariants(events, actual)

    if not any(event.outcome == "FAILED" for event in events):
        assert actual == []

    success_only = [
        Event(
            id=event.id,
            timestamp=event.timestamp,
            source_ip=event.source_ip,
            username=event.username,
            outcome="SUCCESS",
            file_id=event.file_id,
            line_no=event.line_no,
        )
        for event in events
    ]
    assert engine.detect(success_only, threshold=threshold, window_minutes=window_minutes) == []

    first_run = engine.detect(events, threshold=5, window_minutes=window_minutes)
    first_snapshot = deepcopy(first_run)
    engine.detect(events, threshold=3, window_minutes=window_minutes)
    assert first_run == first_snapshot

