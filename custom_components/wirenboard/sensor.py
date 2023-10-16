"""Platform for sensor integration."""

from __future__ import annotations

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.modbus.sensor import ModbusRegisterSensor
from homeassistant.helpers.entity import DeviceInfo
from .const import (DOMAIN)
from .entity import (WbEntity)

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)


from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.const import POWER_VOLT_AMPERE_REACTIVE
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricCurrent
)
from datetime import timedelta

from .wb import WbMap6sDevice

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    
    wb = hass.data[DOMAIN][config_entry.entry_id]
    channels = [1,2,3,4,5,6]

    for device in wb.map6ss:
        coordinator = ModbusSensorCoordinator(hass, device)
        for channel in channels: 
            async_add_entities([WbMap6sCurrentSensor(hass, coordinator, device, channel)])
            async_add_entities([WbMap6sPowerSensor(hass, coordinator, device, channel)])
            async_add_entities([WbMap6sRxPowerSensor(hass, coordinator, device, channel)])
            async_add_entities([WbMap6sEnergySensor(hass, coordinator, device, channel)])
        

class ModbusSensorCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, device: WbMap6sDevice):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Sensor Coordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=1),
        )
        self._device = device

    async def _async_update_data(self):
        await self._device.async_update()




class WbMap6sSensor(WbEntity, CoordinatorEntity[ModbusSensorCoordinator], SensorEntity):
    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusSensorCoordinator,
        device: WbMap6sDevice, channel: int, suffix: str) -> None:
        super().__init__(hass, device, channel, f'{suffix}_channel')
        CoordinatorEntity.__init__(self, coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
    


class WbMap6sCurrentSensor(WbMap6sSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusSensorCoordinator,
        device: WbMap6sDevice, channel: int) -> None:
        super().__init__(hass, coordinator, device, channel, "current")

    @property  
    def native_value(self) -> float:
        return self._device.get_current(self._channel) 


class WbMap6sPowerSensor(WbMap6sSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT

    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusSensorCoordinator,
        device: WbMap6sDevice, channel: int) -> None:
        super().__init__(hass, coordinator, device, channel, "power")

    @property  
    def native_value(self) -> float:
        return self._device.get_power(self._channel) 


class WbMap6sRxPowerSensor(WbMap6sSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.REACTIVE_POWER    
    _attr_native_unit_of_measurement = POWER_VOLT_AMPERE_REACTIVE

    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusSensorCoordinator,
        device: WbMap6sDevice, channel: int) -> None:
        super().__init__(hass, coordinator, device, channel, "rx_power")

    @property  
    def native_value(self) -> float:
        return self._device.get_rx_power(self._channel)

class WbMap6sEnergySensor(WbMap6sSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    
    def __init__(
        self, 
        hass: HomeAssistant, 
        coordinator: ModbusSensorCoordinator,
        device: WbMap6sDevice, channel: int) -> None:
        super().__init__(hass, coordinator, device, channel, "energy")

    @property  
    def native_value(self) -> float:
        return self._device.get_energy(self._channel) 