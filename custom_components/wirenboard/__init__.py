"""wirenboard integration."""

from __future__ import annotations

import logging

from .const import (DOMAIN, CONF_MODBUS_HUB, CONF_MDM3_LIST)
from .wb import WirenBoard

from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.components.modbus import ModbusHub #, async_modbus_setup


PLATFORMS: list[str] = [ "light"]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Async setup hass config entry."""

    modbus_hub = entry.data[CONF_MODBUS_HUB]
    mdm3_list = entry.data[CONF_MDM3_LIST]
    mdm3_addresses =  [int(i) for i in mdm3_list.split(',')]

    wb = WirenBoard(hass, modbus_hub, mdm3_addresses)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = wb
    _LOGGER.info("root setup id=%s", entry.entry_id)
    
    await hass.async_add_executor_job(wb.pull_data)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


