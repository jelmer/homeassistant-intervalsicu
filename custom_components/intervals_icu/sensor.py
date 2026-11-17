"""Sensor platform for Intervals.icu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ATHLETE_ID, DOMAIN
from .coordinator import IntervalsIcuCoordinator, IntervalsIcuData


@dataclass(frozen=True, kw_only=True)
class IntervalsIcuSensorEntityDescription(SensorEntityDescription):
    """Describe an Intervals.icu sensor."""

    value_fn: Callable[[IntervalsIcuData], Any]
    available_fn: Callable[[IntervalsIcuData], bool] = lambda _data: True
    attrs_fn: Callable[[IntervalsIcuData], dict[str, Any] | None] | None = None


def _wellness_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for a wellness field."""

    def _get(data: IntervalsIcuData) -> Any:
        if data.wellness is None:
            return None
        return data.wellness.get(key)

    return _get


def _wellness_available(key: str) -> Callable[[IntervalsIcuData], bool]:
    """Create an available function for a wellness field."""

    def _check(data: IntervalsIcuData) -> bool:
        if data.wellness is None:
            return False
        return data.wellness.get(key) is not None

    return _check


def _latest_activity_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for the latest activity field."""

    def _get(data: IntervalsIcuData) -> Any:
        if not data.activities:
            return None
        return data.activities[0].get(key)

    return _get


def _latest_activity_available(data: IntervalsIcuData) -> bool:
    return len(data.activities) > 0


def _next_event_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for the next planned event."""

    def _get(data: IntervalsIcuData) -> Any:
        workouts = [e for e in data.events if e.get("category") == "WORKOUT"]
        if not workouts:
            return None
        return workouts[0].get(key)

    return _get


def _next_workout_date(data: IntervalsIcuData) -> date | None:
    value = _next_event_value("start_date_local")(data)
    if value is None:
        return None
    return date.fromisoformat(value[:10])


def _next_event_available(data: IntervalsIcuData) -> bool:
    return any(e.get("category") == "WORKOUT" for e in data.events)


def _form_value(data: IntervalsIcuData) -> float | None:
    """Calculate form (TSB) = CTL - ATL."""
    if data.wellness is None:
        return None
    ctl = data.wellness.get("ctl")
    atl = data.wellness.get("atl")
    if ctl is None or atl is None:
        return None
    return round(ctl - atl, 1)


def _form_available(data: IntervalsIcuData) -> bool:
    """Check if form can be calculated."""
    if data.wellness is None:
        return False
    return data.wellness.get("ctl") is not None and data.wellness.get("atl") is not None


def _athlete_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for an athlete top-level field."""

    def _get(data: IntervalsIcuData) -> Any:
        return data.athlete.get(key)

    return _get


def _sport_setting_value(key: str) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for a field in the default sport settings."""

    def _get(data: IntervalsIcuData) -> Any:
        settings = data.athlete.get("sportSettings")
        if not settings:
            return None
        return settings[0].get(key)

    return _get


def _sport_setting_available(key: str) -> Callable[[IntervalsIcuData], bool]:
    """Create an available function for a field in the default sport settings."""

    def _check(data: IntervalsIcuData) -> bool:
        settings = data.athlete.get("sportSettings")
        if not settings:
            return False
        return settings[0].get(key) is not None

    return _check


SENSOR_DESCRIPTIONS: tuple[IntervalsIcuSensorEntityDescription, ...] = (
    # Wellness sensors
    IntervalsIcuSensorEntityDescription(
        key="weight",
        translation_key="weight",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("weight"),
        available_fn=_wellness_available("weight"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="resting_hr",
        translation_key="resting_hr",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("restingHR"),
        available_fn=_wellness_available("restingHR"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="hrv",
        translation_key="hrv",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("hrv"),
        available_fn=_wellness_available("hrv"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="sleep_time",
        translation_key="sleep_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("sleepSecs"),
        available_fn=_wellness_available("sleepSecs"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="sleep_score",
        translation_key="sleep_score",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("sleepScore"),
        available_fn=_wellness_available("sleepScore"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="readiness",
        translation_key="readiness",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("readiness"),
        available_fn=_wellness_available("readiness"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="spo2",
        translation_key="spo2",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("spO2"),
        available_fn=_wellness_available("spO2"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="steps",
        translation_key="steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_wellness_value("steps"),
        available_fn=_wellness_available("steps"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="ctl",
        translation_key="ctl",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("ctl"),
        available_fn=_wellness_available("ctl"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="atl",
        translation_key="atl",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("atl"),
        available_fn=_wellness_available("atl"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="ramp_rate",
        translation_key="ramp_rate",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("rampRate"),
        available_fn=_wellness_available("rampRate"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="form",
        translation_key="form",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_form_value,
        available_fn=_form_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="stress",
        translation_key="stress",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("stress"),
        available_fn=_wellness_available("stress"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="mood",
        translation_key="mood",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("mood"),
        available_fn=_wellness_available("mood"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="motivation",
        translation_key="motivation",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("motivation"),
        available_fn=_wellness_available("motivation"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="fatigue",
        translation_key="fatigue",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("fatigue"),
        available_fn=_wellness_available("fatigue"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="soreness",
        translation_key="soreness",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("soreness"),
        available_fn=_wellness_available("soreness"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="hrv_rmssd",
        translation_key="hrv_rmssd",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("hrvSDNN"),
        available_fn=_wellness_available("hrvSDNN"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="kcal_consumed",
        translation_key="kcal_consumed",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_wellness_value("kcalConsumed"),
        available_fn=_wellness_available("kcalConsumed"),
    ),
    # Latest activity sensors
    IntervalsIcuSensorEntityDescription(
        key="last_activity_name",
        translation_key="last_activity_name",
        value_fn=_latest_activity_value("name"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_type",
        translation_key="last_activity_type",
        value_fn=_latest_activity_value("type"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_duration",
        translation_key="last_activity_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=_latest_activity_value("moving_time"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_distance",
        translation_key="last_activity_distance",
        native_unit_of_measurement="m",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("distance"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_training_load",
        translation_key="last_activity_training_load",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("icu_training_load"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_avg_hr",
        translation_key="last_activity_avg_hr",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("average_heartrate"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_max_hr",
        translation_key="last_activity_max_hr",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("max_heartrate"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_avg_cadence",
        translation_key="last_activity_avg_cadence",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("average_cadence"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_avg_power",
        translation_key="last_activity_avg_power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("icu_average_watts"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_np",
        translation_key="last_activity_np",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("icu_weighted_avg_watts"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_intensity",
        translation_key="last_activity_intensity",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("icu_intensity"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_calories",
        translation_key="last_activity_calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("calories"),
        available_fn=_latest_activity_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="last_activity_elevation",
        translation_key="last_activity_elevation",
        native_unit_of_measurement="m",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest_activity_value("total_elevation_gain"),
        available_fn=_latest_activity_available,
    ),
    # Next planned workout sensors
    IntervalsIcuSensorEntityDescription(
        key="next_workout_name",
        translation_key="next_workout_name",
        value_fn=_next_event_value("name"),
        available_fn=_next_event_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="next_workout_date",
        translation_key="next_workout_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=_next_workout_date,
        available_fn=_next_event_available,
    ),
    IntervalsIcuSensorEntityDescription(
        key="next_workout_type",
        translation_key="next_workout_type",
        value_fn=_next_event_value("type"),
        available_fn=_next_event_available,
    ),
    # Athlete fitness metrics (FTP, LTHR, max HR are per-sport in sportSettings)
    IntervalsIcuSensorEntityDescription(
        key="ftp",
        translation_key="ftp",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sport_setting_value("ftp"),
        available_fn=_sport_setting_available("ftp"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="lthr",
        translation_key="lthr",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sport_setting_value("lthr"),
        available_fn=_sport_setting_available("lthr"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="max_hr",
        translation_key="max_hr",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sport_setting_value("max_hr"),
        available_fn=_sport_setting_available("max_hr"),
    ),
    IntervalsIcuSensorEntityDescription(
        key="resting_hr_athlete",
        translation_key="resting_hr_athlete",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_athlete_value("icu_resting_hr"),
        available_fn=lambda data: data.athlete.get("icu_resting_hr") is not None,
    ),
)


_NAMED_DISTANCES: tuple[tuple[float, str], ...] = (
    (1609.34, "1 mile"),
    (3218.69, "2 miles"),
    (5000.0, "5k"),
    (10000.0, "10k"),
    (16093.4, "10 miles"),
    (21097.5, "half marathon"),
    (42195.0, "marathon"),
)


def _format_distance(meters: float) -> str:
    """Format a distance in meters as a short human-readable label."""
    for value, label in _NAMED_DISTANCES:
        if abs(meters - value) < 1.0:
            return label
    if meters >= 1000:
        km = meters / 1000
        if km == int(km):
            return f"{int(km)}k"
        return f"{km:g}k"
    return f"{round(meters)}m"


def _best_effort_value(index: int) -> Callable[[IntervalsIcuData], Any]:
    """Create a value function for the best effort at a distance index."""

    def _get(data: IntervalsIcuData) -> Any:
        curve = data.pace_curve
        if not curve:
            return None
        values = curve.get("values") or []
        if index >= len(values):
            return None
        return values[index]

    return _get


def _best_effort_available(index: int) -> Callable[[IntervalsIcuData], bool]:
    """Return True when the pace curve has a value at the given index."""

    def _check(data: IntervalsIcuData) -> bool:
        curve = data.pace_curve
        if not curve:
            return False
        values = curve.get("values") or []
        return index < len(values) and values[index] is not None

    return _check


def _best_effort_attrs(
    index: int,
) -> Callable[[IntervalsIcuData], dict[str, Any] | None]:
    """Return the activity id/name/date that set the best effort at this index."""

    def _get(data: IntervalsIcuData) -> dict[str, Any] | None:
        curve = data.pace_curve
        if not curve:
            return None
        activity_ids = curve.get("activity_id") or []
        if index >= len(activity_ids):
            return None
        activity_id = activity_ids[index]
        return {"activity_id": activity_id}

    return _get


def _best_effort_sensors(
    data: IntervalsIcuData,
) -> tuple[IntervalsIcuSensorEntityDescription, ...]:
    """Build one sensor description per distance in the pace curve."""
    curve = data.pace_curve
    if not curve:
        return ()
    distances = curve.get("distance") or []
    return tuple(
        IntervalsIcuSensorEntityDescription(
            key=f"best_effort_{round(meters)}m",
            name=f"Best effort {_format_distance(meters)}",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_best_effort_value(index),
            available_fn=_best_effort_available(index),
            attrs_fn=_best_effort_attrs(index),
        )
        for index, meters in enumerate(distances)
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intervals.icu sensors from a config entry."""
    coordinator: IntervalsIcuCoordinator = hass.data[DOMAIN][entry.entry_id]
    athlete_id = entry.data[CONF_ATHLETE_ID]

    descriptions = SENSOR_DESCRIPTIONS + _best_effort_sensors(coordinator.data)
    async_add_entities(
        IntervalsIcuSensor(coordinator, description, athlete_id)
        for description in descriptions
    )


class IntervalsIcuSensor(CoordinatorEntity[IntervalsIcuCoordinator], SensorEntity):
    """Representation of an Intervals.icu sensor."""

    entity_description: IntervalsIcuSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IntervalsIcuCoordinator,
        description: IntervalsIcuSensorEntityDescription,
        athlete_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{athlete_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, athlete_id)},
            name="Intervals.icu",
            manufacturer="Intervals.icu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            return False
        return self.entity_description.available_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes, if the description provides them."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
