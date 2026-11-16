"""Tests for the Intervals.icu sensor platform."""

from __future__ import annotations

import unittest
from datetime import date

from custom_components.intervals_icu.coordinator import IntervalsIcuData
from custom_components.intervals_icu.sensor import SENSOR_DESCRIPTIONS


def _description(key: str):
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


class TestNextWorkoutDate(unittest.TestCase):
    def _data(self, events: list[dict]) -> IntervalsIcuData:
        return IntervalsIcuData(
            athlete={},
            wellness=None,
            activities=[],
            events=events,
            pace_curve=None,
        )

    def test_returns_date(self) -> None:
        data = self._data(
            [{"category": "WORKOUT", "start_date_local": "2026-11-16T05:45:00"}]
        )
        self.assertEqual(
            date(2026, 11, 16), _description("next_workout_date").value_fn(data)
        )

    def test_no_workout(self) -> None:
        data = self._data([{"category": "NOTE", "start_date_local": "2026-11-16"}])
        self.assertIsNone(_description("next_workout_date").value_fn(data))
