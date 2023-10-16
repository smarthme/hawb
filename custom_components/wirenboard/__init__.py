"""wirenboard integration."""

from __future__ import annotations

import logging

from .const import (DOMAIN, CONF_MODBUS_HUB, CONF_MDM3_LIST, CONF_MAP6S_LIST)
from .wb import WirenBoard

from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.components.modbus import ModbusHub


PLATFORMS: list[str] = [ "light", "sensor"]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Async setup hass config entry."""

    modbus_hub = entry.data[CONF_MODBUS_HUB]
    
    
    mdm3_list = entry.data.get(CONF_MDM3_LIST, '')
    mdm3_addresses = to_number_array(mdm3_list)

    map6s_list = entry.data.get(CONF_MAP6S_LIST, '')
    map6s_addresses = to_number_array(map6s_list)

    wb = WirenBoard(hass, modbus_hub, mdm3_addresses, map6s_addresses)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = wb
    _LOGGER.info("root setup id=%s", entry.entry_id)
    
    await hass.async_add_executor_job(wb.pull_data)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

def to_number_array(string_list):
    if (string_list == None):
        return []
    if (string_list == ''):
        return []
    return [int(i) for i in string_list.split(',')]
    

