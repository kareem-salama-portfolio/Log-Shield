"""Generate deterministic synthetic authentication logs."""

import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
IPS = (
    "192.0.2.10",
    "198.51.100.23",
    "203.0.113.7",
    "192.0.2.44",
    "198.51.100.42",
    "203.0.113.19",
)


def format_line(ts, outcome, user, ip, n):
    verb = "Failed" if outcome == "FAILED" else "Accepted"
    user_part = f"invalid user {user[8:]}" if user.startswith("invalid_") else user
    return f"{ts.isoformat(timespec='seconds')} sshd[{n}]: {verb} password for {user_part} from {ip} port {40000 + n % 20000}"


def main():
    DATA.mkdir(exist_ok=True)
    rng = random.Random(20261023)
    start = datetime(2026, 10, 2)
    rows = []
    for i in range(1050):
        rows.append(
            (
                start + timedelta(seconds=i * 165),
                "FAILED" if rng.random() < 0.28 else "SUCCESS",
                rng.choice(("admin", "operator", "service", "invalid_guest")),
                rng.choice(IPS),
            )
        )
    base = datetime(2026, 10, 2, 8, 0, 10)
    for sec in (0, 140, 230, 455, 585):
        rows.append((base + timedelta(seconds=sec), "FAILED", "admin", "203.0.113.7"))
    rows.append((base + timedelta(seconds=710), "SUCCESS", "admin", "203.0.113.7"))
    for base, ip in (
        (datetime(2026, 10, 2, 13), "192.0.2.44"),
        (datetime(2026, 10, 3, 6), "198.51.100.42"),
    ):
        for sec in (0, 60, 125, 220, 300):
            rows.append((base + timedelta(seconds=sec), "FAILED", "root", ip))
        rows.append((base + timedelta(minutes=7), "SUCCESS", "root", ip))
    near = datetime(2026, 10, 3, 10)
    for sec in (0, 240, 480, 840):
        rows.append((near + timedelta(seconds=sec), "FAILED", "admin", "198.51.100.23"))
    rows.sort(key=lambda row: row[0])
    lines = [format_line(*row, n + 1) for n, row in enumerate(rows)]
    lines += [
        "2026-10-03T11:00:00 sshd[bad]: Failed password for admin from 999.1.1.1 port 22",
        "yesterday sshd[12]: Failed password for admin from 203.0.113.7 port 22",
        "not an authentication line",
        "2026-10-03T11:00:00 sshd[13]: Failed password for admin from 203.0.113.7 port nope",
        "2026-10-03T11:00:00+00:00 sshd[14]: Accepted password for guest from 192.0.2.10 port 22",
        "2026-10-03T11:00:00 sshd[15]: Failed password for from 192.0.2.10 port 22",
        "broken timestamp sshd[16]: Accepted password for guest from 192.0.2.10 port 22",
        "2026-10-03T11:00:00 sshd[17]: Unknown password for guest from 192.0.2.10 port 22",
        "",
        "<malformed>",
    ]
    (DATA / "auth_sample.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (DATA / "duplicate_check.log").write_text(
        "2026-10-04T08:00:00 sshd[1]: Failed password for admin from 192.0.2.10 port 2201\n2026-10-04T08:01:00 sshd[2]: Accepted password for admin from 192.0.2.10 port 2202\nintentionally malformed line\n",
        encoding="utf-8",
    )
    print(f"{len(lines)} sample lines generated")


if __name__ == "__main__":
    main()
