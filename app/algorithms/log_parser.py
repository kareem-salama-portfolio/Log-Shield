"""Parser for the supported sshd authentication-log format."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from ipaddress import ip_address

from app.models.event import Event, MalformedRecord

_AUTH_LINE = re.compile(
    r"^(?P<timestamp>\S+)\s+sshd\[\d+\]:\s+"
    r"(?P<action>Failed|Accepted) password for "
    r"(?:(?:invalid user)\s+)?(?P<username>\S+)\s+"
    r"from\s+(?P<source_ip>\S+)\s+port\s+\d+$"
)


class LogParser:
    """Convert supported authentication-log lines into shared models."""

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is not None:
            raise ValueError("timestamp must be naive")
        return timestamp

    def parse_line(self, raw_line: str, line_no: int) -> Event | MalformedRecord:
        """Parse one raw line without raising for malformed input."""

        line = raw_line.strip()
        match = _AUTH_LINE.match(line)
        if match is None:
            return MalformedRecord(
                line_no=line_no,
                line_raw=raw_line,
                reason="UNKNOWN_PATTERN",
            )

        values = match.groupdict()
        try:
            timestamp = self._parse_timestamp(values["timestamp"])
        except (TypeError, ValueError):
            return MalformedRecord(
                line_no=line_no,
                line_raw=raw_line,
                reason="BAD_TIMESTAMP",
            )

        try:
            ip_address(values["source_ip"])
        except ValueError:
            return MalformedRecord(
                line_no=line_no,
                line_raw=raw_line,
                reason="INVALID_IP",
            )

        return Event(
            id=None,
            timestamp=timestamp,
            source_ip=str(ip_address(values["source_ip"])),
            username=values["username"],
            outcome="FAILED" if values["action"] == "Failed" else "SUCCESS",
            file_id=None,
            line_no=line_no,
        )

    def parse_lines(
        self,
        lines: Iterable[str],
        *,
        start_line_no: int = 1,
    ) -> tuple[list[Event], list[MalformedRecord]]:
        """Parse an iterable, retaining valid and malformed records separately."""

        events: list[Event] = []
        malformed: list[MalformedRecord] = []
        for offset, raw_line in enumerate(lines):
            result = self.parse_line(raw_line, start_line_no + offset)
            if isinstance(result, Event):
                events.append(result)
            else:
                malformed.append(result)
        return events, malformed

