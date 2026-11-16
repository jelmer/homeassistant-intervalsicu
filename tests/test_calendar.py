"""Tests for the Intervals.icu calendar platform."""

from __future__ import annotations

import unittest
import zoneinfo
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

from homeassistant.util import dt as dt_util

from custom_components.intervals_icu.calendar import (
    IntervalsIcuCalendar,
    _event_to_calendar_event,
)
from custom_components.intervals_icu.coordinator import IntervalsIcuData


class TestEventToCalendarEvent(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_tz = dt_util.get_default_time_zone()
        dt_util.set_default_time_zone(zoneinfo.ZoneInfo("Europe/Berlin"))

    def tearDown(self) -> None:
        dt_util.set_default_time_zone(self._orig_tz)

    def test_local_datetime_is_timezone_aware(self) -> None:
        cal_event = _event_to_calendar_event(
            {
                "category": "WORKOUT",
                "name": "Intervals",
                "start_date_local": "2026-11-16T05:45:00",
                "moving_time": 3600,
            }
        )
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        self.assertEqual(datetime(2026, 11, 16, 5, 45, tzinfo=tz), cal_event.start)
        self.assertEqual(datetime(2026, 11, 16, 6, 45, tzinfo=tz), cal_event.end)

    def test_date_is_all_day(self) -> None:
        cal_event = _event_to_calendar_event(
            {"category": "NOTE", "name": "Rest", "start_date_local": "2026-11-16"}
        )
        self.assertEqual(date(2026, 11, 16), cal_event.start)
        self.assertEqual(date(2026, 11, 17), cal_event.end)


class TestCalendarEvent(unittest.TestCase):
    def _calendar(self, events: list[dict]) -> IntervalsIcuCalendar:
        coordinator = MagicMock()
        coordinator.data = IntervalsIcuData(
            athlete={},
            wellness=None,
            activities=[],
            events=events,
            pace_curve=None,
        )
        return IntervalsIcuCalendar(coordinator, "i12345")

    def test_next_timed_event(self) -> None:
        start = dt_util.now().replace(microsecond=0, tzinfo=None) + timedelta(days=1)
        calendar = self._calendar(
            [
                {
                    "category": "WORKOUT",
                    "name": "Intervals",
                    "start_date_local": start.isoformat(),
                }
            ]
        )
        event = calendar.event
        assert event is not None
        self.assertEqual("Intervals", event.summary)

    def test_skips_ended_all_day_event(self) -> None:
        today = dt_util.now().date()
        calendar = self._calendar(
            [
                {
                    "category": "NOTE",
                    "name": "Yesterday",
                    "start_date_local": (today - timedelta(days=1)).isoformat(),
                },
                {
                    "category": "NOTE",
                    "name": "Today",
                    "start_date_local": today.isoformat(),
                },
            ]
        )
        event = calendar.event
        assert event is not None
        self.assertEqual("[Note] Today", event.summary)
