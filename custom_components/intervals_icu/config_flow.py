"""Config flow for Intervals.icu integration."""

from __future__ import annotations

import logging
from typing import Any

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IntervalsIcuApiError, IntervalsIcuAuthError, IntervalsIcuClient
from .const import CONF_API_KEY, CONF_ATHLETE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_ATHLETE_ID): str,
        probatio.Required(CONF_API_KEY): str,
    }
)


class IntervalsIcuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Intervals.icu."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            athlete_id = user_input[CONF_ATHLETE_ID]
            api_key = user_input[CONF_API_KEY]

            await self.async_set_unique_id(athlete_id)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = IntervalsIcuClient(session, athlete_id, api_key)

            try:
                athlete = await client.validate_credentials()
            except IntervalsIcuAuthError:
                errors["base"] = "invalid_auth"
            except IntervalsIcuApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                name = athlete.get("name") or athlete.get("firstname") or athlete_id
                return self.async_create_entry(
                    title=f"Intervals.icu ({name})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
