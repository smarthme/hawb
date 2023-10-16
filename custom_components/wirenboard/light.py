"""Platform for light integration."""
from __future__ import annotations

import logging
from .const import (DOMAIN)
from .entity import (WbEntity)
from datetime import timedelta
from .wb import (WbMdm3Device, WbLightDevice)
from homeassistant.components.light import (ATTR_BRIGHTNESS, ColorMode, LightEntity)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    wb = hass.data[DOMAIN][config_entry.entry_id]

    for device in wb.mdm3s:
        coordinator = ModbusLightCoordinator(hass, device)
        for channel in range(0, device.channels): 
            async_add_entities([WbMdm3Light(hass, coordinator, device, channel)])


class WbLight(WbEntity, CoordinatorEntity, LightEntity):
    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusLightCoordinator,
        device: WbLightDevice, channel: int
    ) -> None:
        super().__init__(hass, device, channel)
        CoordinatorEntity.__init__(self, coordinator)

        supported_brightness =  device.supported_brightness(channel)

        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF

        if supported_brightness == True:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._device.get_state(self._channel)

    @property
    def brightness(self) -> int:
        return self._device.get_brightness(self._channel) #self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await self._device.async_set_brightness(self._channel, brightness)
        else:
            await self._device.async_turn_on(self._channel)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.async_turn_off(self._channel)



class WbMdm3Light(WbLight):
    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusLightCoordinator,
        device: WbMdm3Device, channel: int
    ) -> None:
        """Initialize an WbLight."""
        super().__init__(hass, coordinator, device, channel)



class ModbusLightCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, device: WbDevice):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Light Coordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=1),
        )
        self._device = device
    

    async def _async_update_data(self):
        await self._device.async_update()
