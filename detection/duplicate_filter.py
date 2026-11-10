from __future__ import annotations

from datetime import datetime, timedelta


class DuplicateFilter:
    def __init__(self, interval_seconds: int = 10) -> None:
        self.interval = timedelta(seconds=interval_seconds)
        self._last_seen: dict[str, datetime] = {}

    def accept(self, plate: str, now: datetime | None = None) -> bool:
        if not plate:
            return False
        current = now or datetime.now()
        previous = self._last_seen.get(plate)
        if previous and current - previous < self.interval:
            return False
        self._last_seen[plate] = current
        return True