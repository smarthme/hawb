"""wirenboard integration."""

from __future__ import annotations
import logging
from typing import Any

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .const import (DOMAIN, CONF_MODBUS_HUB, CONF_MDM3_LIST, CONF_MAP6S_LIST)

_LOGGER = logging.getLogger(__name__)

class WbConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_MODBUS_HUB], data=user_input)

        data_schema = {
            vol.Required(CONF_MODBUS_HUB): str,
            vol.Optional(CONF_MDM3_LIST): str,
            vol.Optional(CONF_MAP6S_LIST): str
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema)
        )

