"""Sliding-window brute-force detection."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from datetime import timedelta
from typing import TYPE_CHECKING

from app.models.incident import Incident
from app.utils.errors import ValidationError

if TYPE_CHECKING:
    from app.models.event import Event


class DetectionEngine:
    """Detect repeated failed events independently for each source IP."""

    def detect(
        self,
        events: Iterable[Event],
        threshold: int = 5,
        window_minutes: int = 10,
    ) -> list[Incident]:
        """Return incidents for IPs reaching ``threshold`` failures in a window.

        Events are copied into a sorted list, so the caller's iterable and any
        list supplied to this method are never changed.  A window includes both
        endpoints: failures exactly ``window_minutes`` apart are retained.
        """

        self._validate_params(threshold, window_minutes)

        ordered_events = sorted(events, key=lambda event: (event.timestamp, event.line_no))
        window = timedelta(minutes=window_minutes)
        recent_by_ip: dict[str, deque[Event]] = {}
        open_incident_by_ip: dict[str, Incident] = {}
        evidence_by_incident: dict[int, list[Event]] = {}
        linked_failures_by_incident: dict[int, set[int]] = {}
        incidents: list[Incident] = []

        for event in ordered_events:
            self._process_event(
                event,
                threshold,
                window,
                recent_by_ip,
                open_incident_by_ip,
                evidence_by_incident,
                linked_failures_by_incident,
                incidents,
            )
        self._finalize_evidence(incidents, evidence_by_incident)
        return incidents

    @staticmethod
    def _process_event(
        event: Event,
        threshold: int,
        window: timedelta,
        recent_by_ip: dict[str, deque[Event]],
        open_incident_by_ip: dict[str, Incident],
        evidence_by_incident: dict[int, list[Event]],
        linked_failures_by_incident: dict[int, set[int]],
        incidents: list[Incident],
    ) -> None:
        if event.id is None:
            raise ValidationError("events must have an id before detection")
        if event.outcome == "SUCCESS":
            DetectionEngine._process_success_event(
                event, window, open_incident_by_ip, evidence_by_incident
            )
        elif event.outcome == "FAILED":
            DetectionEngine._process_failed_event(
                event,
                threshold,
                window,
                recent_by_ip,
                open_incident_by_ip,
                evidence_by_incident,
                linked_failures_by_incident,
                incidents,
            )

    @staticmethod
    def _process_success_event(
        event: Event,
        window: timedelta,
        open_incident_by_ip: dict[str, Incident],
        evidence_by_incident: dict[int, list[Event]],
    ) -> None:
        incident = open_incident_by_ip.get(event.source_ip)
        if incident is not None:
            DetectionEngine._record_success(
                event,
                incident,
                window,
                evidence_by_incident[id(incident)],
            )

    @staticmethod
    def _process_failed_event(
        event: Event,
        threshold: int,
        window: timedelta,
        recent_by_ip: dict[str, deque[Event]],
        open_incident_by_ip: dict[str, Incident],
        evidence_by_incident: dict[int, list[Event]],
        linked_failures_by_incident: dict[int, set[int]],
        incidents: list[Incident],
    ) -> None:
        recent = recent_by_ip.setdefault(event.source_ip, deque())
        recent.append(event)
        while recent and event.timestamp - recent[0].timestamp > window:
            recent.popleft()
        if len(recent) < threshold:
            return

        open_incident = open_incident_by_ip.get(event.source_ip)
        if open_incident is not None and open_incident.end_ts >= event.timestamp - window:
            incident_key = id(open_incident)
            DetectionEngine._merge(
                open_incident,
                event,
                recent,
                evidence_by_incident[incident_key],
                linked_failures_by_incident[incident_key],
            )
            return

        DetectionEngine._open_incident(
            event,
            recent,
            open_incident_by_ip,
            evidence_by_incident,
            linked_failures_by_incident,
            incidents,
        )

    @staticmethod
    def _open_incident(
        event: Event,
        recent: deque[Event],
        open_incident_by_ip: dict[str, Incident],
        evidence_by_incident: dict[int, list[Event]],
        linked_failures_by_incident: dict[int, set[int]],
        incidents: list[Incident],
    ) -> None:
        incident = Incident(
            source_ip=event.source_ip,
            start_ts=recent[0].timestamp,
            end_ts=event.timestamp,
            failure_count=len(recent),
            event_ids=[failed_event.id for failed_event in recent],
        )
        incidents.append(incident)
        open_incident_by_ip[event.source_ip] = incident
        incident_key = id(incident)
        evidence_by_incident[incident_key] = list(recent)
        linked_failures_by_incident[incident_key] = {
            failed_event.id for failed_event in recent
        }

    @staticmethod
    def _finalize_evidence(
        incidents: list[Incident], evidence_by_incident: dict[int, list[Event]]
    ) -> None:
        for incident in incidents:
            evidence = evidence_by_incident[id(incident)]
            incident.event_ids = [
                evidence_event.id
                for evidence_event in sorted(
                    evidence,
                    key=lambda evidence_event: (
                        evidence_event.timestamp,
                        evidence_event.line_no,
                    ),
                )
            ]

    @staticmethod
    def _validate_params(threshold: int, window_minutes: int) -> None:
        if (
            not isinstance(threshold, int)
            or isinstance(threshold, bool)
            or not 3 <= threshold <= 20
        ):
            raise ValidationError("threshold must be an integer between 3 and 20")

        if (
            not isinstance(window_minutes, int)
            or isinstance(window_minutes, bool)
            or not 1 <= window_minutes <= 60
        ):
            raise ValidationError("window_minutes must be an integer between 1 and 60")

    @staticmethod
    def _merge(
        incident: Incident,
        event: Event,
        recent: deque[Event],
        evidence: list[Event],
        linked_failure_ids: set[int],
    ) -> None:
        """Extend an incident with newly observed evidence."""

        new_failures: list[Event] = []
        for failed_event in reversed(recent):
            if failed_event.id in linked_failure_ids:
                break
            new_failures.append(failed_event)

        for failed_event in reversed(new_failures):
            linked_failure_ids.add(failed_event.id)
            evidence.append(failed_event)

        # Success evidence may already be linked, so failure_count must only
        # grow for newly linked FAILED events.
        incident.failure_count += len(new_failures)
        incident.end_ts = event.timestamp

    @staticmethod
    def _record_success(
        event: Event,
        incident: Incident,
        window: timedelta,
        evidence: list[Event],
    ) -> None:
        """Link an in-window success to its source IP's open incident."""

        elapsed = event.timestamp - incident.end_ts
        if timedelta(0) <= elapsed <= window:
            incident.severity = "HIGH"
            evidence.append(event)

