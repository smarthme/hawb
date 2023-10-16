"""wirenboard integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from .wb import WbDevice
from .const import (DOMAIN)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

class WbEntity(Entity):
    def __init__(self, hass: HomeAssistant,  device: WbDevice, channel: int, prefix: str  = "channel") -> None:
        self._hass = hass
        self._device = device
        self._channel = channel
        slave = device.slave
        short_name = device.short_name
        self._unique_id = "{short_name}_{slave}_{prefix}_{channel}".format(short_name = short_name, slave = slave, prefix = prefix, channel = channel)

        self._name = self._unique_id


    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        short_name = self._device.short_name
        return DeviceInfo(
            identifiers={
                (DOMAIN, "{short_name}-{slave}".format(short_name = short_name, slave = self._device.slave))
            },
            name = "{short_name}-{slave}".format(short_name = short_name, slave = self._device.slave),
            model = self._device.model,
            sw_version = self._device.firmware,
            manufacturer = self._device.manufacturer
        )

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

            
    @property
    def unique_id(self) -> str:
        """Return the display name of this light."""
        return self._unique_id