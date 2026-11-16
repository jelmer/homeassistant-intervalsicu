"""Calendar platform for Intervals.icu."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import IntervalsIcuApiError
from .const import CONF_ATHLETE_ID, DOMAIN
from .coordinator import IntervalsIcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intervals.icu calendar from a config entry."""
    coordinator: IntervalsIcuCoordinator = hass.data[DOMAIN][entry.entry_id]
    athlete_id = entry.data[CONF_ATHLETE_ID]

    async_add_entities([IntervalsIcuCalendar(coordinator, athlete_id)])


def _parse_event_datetime(
    date_str: str | None, fallback_date: date | None = None
) -> datetime | date:
    """Parse an Intervals.icu date/datetime string."""
    if date_str is None:
        return fallback_date or date.today()
    # Intervals.icu uses "2024-01-15T00:00:00" for local datetimes
    if "T" in date_str:
        parsed = datetime.fromisoformat(date_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
        return parsed
    return date.fromisoformat(date_str)


def _event_to_calendar_event(event: dict[str, Any]) -> CalendarEvent:
    """Convert an Intervals.icu event to a CalendarEvent."""
    name = event.get("name") or event.get("type") or "Workout"
    category = event.get("category", "")
    event_type = event.get("type", "")

    if category and category != "WORKOUT":
        name = f"[{category.title()}] {name}"

    start = _parse_event_datetime(event.get("start_date_local"))
    moving_time = event.get("moving_time")

    end: datetime | date
    if isinstance(start, datetime) and moving_time:
        end = start + timedelta(seconds=moving_time)
    elif isinstance(start, datetime):
        # Default to 1 hour if no duration
        end = start + timedelta(hours=1)
    else:
        # All-day event
        end = start + timedelta(days=1)

    description_parts: list[str] = []
    if event_type:
        description_parts.append(f"Type: {event_type}")
    if event.get("description"):
        description_parts.append(event["description"])
    load = event.get("icu_training_load")
    if load:
        description_parts.append(f"Training Load: {load}")

    return CalendarEvent(
        summary=name,
        start=start,
        end=end,
        description="\n".join(description_parts) if description_parts else None,
    )


class IntervalsIcuCalendar(CoordinatorEntity[IntervalsIcuCoordinator], CalendarEntity):
    """Intervals.icu calendar showing planned workouts and events."""

    _attr_has_entity_name = True
    _attr_name = "Training calendar"

    def __init__(
        self,
        coordinator: IntervalsIcuCoordinator,
        athlete_id: str,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._athlete_id = athlete_id
        self._attr_unique_id = f"{athlete_id}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, athlete_id)},
            name="Intervals.icu",
            manufacturer="Intervals.icu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event from coordinator data."""
        if not self.coordinator.data or not self.coordinator.data.events:
            return None
        now = dt_util.now()
        for ev in self.coordinator.data.events:
            if ev.get("category") not in ("WORKOUT", "TARGET", "NOTE", "RACE"):
                continue
            cal_event = _event_to_calendar_event(ev)
            # Include events that haven't ended yet
            event_end = cal_event.end
            if not isinstance(event_end, datetime):
                # All-day event ends are exclusive
                event_end = dt_util.start_of_local_day(event_end)
            if event_end > now:
                return cal_event
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Fetch events from the API for a date range."""
        client = self.coordinator.client
        try:
            events = await client.get_events(
                oldest=start_date.date(),
                newest=end_date.date(),
            )
        except IntervalsIcuApiError:
            _LOGGER.exception("Error fetching calendar events")
            return []

        return [
            _event_to_calendar_event(ev)
            for ev in events
            if ev.get("category") in ("WORKOUT", "TARGET", "NOTE", "RACE")
        ]
