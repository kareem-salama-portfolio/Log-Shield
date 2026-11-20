"""Plain data contract consumed by the Security Overview Dashboard."""

from typing import TypedDict


class FailedPerHourPoint(TypedDict):
    hour: str
    failure_count: int


class TopSourceIP(TypedDict):
    source_ip: str
    failure_count: int


class IncidentSummary(TypedDict):
    source_ip: str
    start_time: str
    end_time: str
    failure_count: int
    severity: str
    status: str


class DashboardData(TypedDict):
    total_events: int
    failed_logins: int
    unique_ips: int
    medium_incidents: int
    high_incidents: int
    failed_per_hour: list[FailedPerHourPoint]
    top_ips: list[TopSourceIP]
    latest_incidents: list[IncidentSummary]
