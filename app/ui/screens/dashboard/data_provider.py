"""Temporary dashboard data adapter for empty and visual-demo modes.

This module contains no persistence or analysis logic. A future application
service can supply the same plain ``DashboardData`` contract to the screen.
"""

from app.models.dashboard import DashboardData


def get_empty_dashboard_data() -> DashboardData:
    """Return an honest zero-event snapshot for a new local workspace."""
    return {
        "total_events": 0,
        "failed_logins": 0,
        "unique_ips": 0,
        "medium_incidents": 0,
        "high_incidents": 0,
        "failed_per_hour": [],
        "top_ips": [],
        "latest_incidents": [],
    }


def get_demo_dashboard_data() -> DashboardData:
    """Return fixed, clearly synthetic values for visual development only."""
    return {
        "total_events": 1240,
        "failed_logins": 340,
        "unique_ips": 42,
        "medium_incidents": 3,
        "high_incidents": 1,
        "failed_per_hour": [
            {"hour": "07:00", "failure_count": 14},
            {"hour": "08:00", "failure_count": 18},
            {"hour": "09:00", "failure_count": 12},
            {"hour": "10:00", "failure_count": 22},
            {"hour": "11:00", "failure_count": 28},
            {"hour": "12:00", "failure_count": 24},
            {"hour": "13:00", "failure_count": 31},
            {"hour": "14:00", "failure_count": 35},
            {"hour": "15:00", "failure_count": 29},
            {"hour": "16:00", "failure_count": 41},
            {"hour": "17:00", "failure_count": 43},
            {"hour": "18:00", "failure_count": 43},
        ],
        "top_ips": [
            {"source_ip": "203.0.113.87", "failure_count": 62},
            {"source_ip": "198.51.100.42", "failure_count": 48},
            {"source_ip": "192.0.2.128", "failure_count": 39},
            {"source_ip": "198.51.100.73", "failure_count": 31},
            {"source_ip": "203.0.113.19", "failure_count": 24},
        ],
        "latest_incidents": [
            {
                "source_ip": "203.0.113.87",
                "start_time": "2026-11-20T14:12:00",
                "end_time": "2026-11-20T14:26:00",
                "failure_count": 62,
                "severity": "HIGH",
                "status": "Investigating",
            },
            {
                "source_ip": "198.51.100.42",
                "start_time": "2026-11-20T12:08:00",
                "end_time": "2026-11-20T12:11:00",
                "failure_count": 48,
                "severity": "MEDIUM",
                "status": "Open",
            },
            {
                "source_ip": "192.0.2.128",
                "start_time": "2026-11-20T10:51:00",
                "end_time": "2026-11-20T11:02:00",
                "failure_count": 39,
                "severity": "MEDIUM",
                "status": "Resolved",
            },
            {
                "source_ip": "198.51.100.73",
                "start_time": "2026-11-20T09:18:00",
                "end_time": "2026-11-20T09:20:00",
                "failure_count": 31,
                "severity": "MEDIUM",
                "status": "Open",
            },
        ],
    }
