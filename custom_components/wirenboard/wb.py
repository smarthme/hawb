"""Platform for sensor integration."""

from __future__ import annotations
from homeassistant.core import HomeAssistant
from typing import cast
from homeassistant.components.modbus import ModbusHub #, async_modbus_setup
import logging

_LOGGER = logging.getLogger(__name__)

def get_modbus_hub(hass: HomeAssistant, name: str) -> ModbusHub:
    """Return modbus hub with name."""
    return cast(ModbusHub, hass.data["modbus"][name])

class WirenBoard:
    def __init__(self, hass: HomeAssistant, modbus_hub: str, mdm3_addresses) -> None:
        self._modbus_hub = modbus_hub
        self.mdm3s = []
        self.hass = hass
        self.mdm3_addresses = mdm3_addresses


    def pull_data(self):
        hub = get_modbus_hub(self.hass, self._modbus_hub)
        for slave in self.mdm3_addresses:
            self.mdm3s.append(WbMdm3Device(self.hass, hub, slave))


class WbDevice:
    def __init__(self, hass: HomeAssistant, hub: ModbusHub, slave: int) -> None:
        self._hass = hass
        self._slave = slave
        self._hub = hub

    @property
    def slave(self) -> int:
        return self._slave

    @property
    def model(self) -> str:
        model_bytes = self.read_inputs(200, 6)
        return "".join(map(chr, model_bytes))

    @property
    def firmware(self) -> str:
        firmware_bytes = self.read_inputs(250, 15)
        bootloader_bytes = self.read_inputs(330, 5)
        firmware = "".join(map(chr, firmware_bytes))
        bootloader = "".join(map(chr, bootloader_bytes))
        return firmware + " (bootloader " + bootloader + ")" 

    @property
    def manufacturer(self) -> str:
        return "wirenboard"

    async def async_write_coil(self, address: int, value: bool) -> None:
        await self._hub.async_pb_call(self._slave, address, value, "write_coil")

    async def async_write_holding(self, address: int, value: int) -> None:
        await self._hub.async_pb_call(self._slave, address, value, "write_register")
        
    async def async_read_coils(self, address: int, count: int):
        raw_result = await self._hub.async_pb_call(self._slave, address, count, "coil")
        if raw_result is None:
            _LOGGER.info("read_coils %s Null", self._slave)
            return None
        else:
            return raw_result.bits

    async def async_read_holding(self, address: int, count: int):
        raw_result = await self._hub.async_pb_call(self._slave, address, count, "holding")

        if raw_result is None:
            _LOGGER.info("read_holding %s Null", self._slave)
            return None
        else:
            return raw_result.registers

    def read_holding(self, address: int, count: int):
        raw_result = self._hub.pb_call(self._slave, address, count, "holding")

        if raw_result is None:
            _LOGGER.info("read_holding %s Null", self._slave)
            return None
        else:
            return raw_result.registers

    async def async_read_discrete_input(self, address: int, count: int):
        raw_result = await self._hub.async_pb_call(self._slave, address, count, "discrete_input")
        if raw_result is None:
            _LOGGER.info("read_discrete_input %s Null", self._slave)
            return None
        else:
            return raw_result.bits  

    async def async_read_inputs(self, address: int, count: int):
        raw_result = await self._hub.async_pb_call(self._slave, address, count, "input")
        if raw_result is None:
            _LOGGER.info("read_inputs %s Null", self._slave)
            return None
        else:
            return raw_result.registers  

    def read_inputs(self, address: int, count: int):
        raw_result =  self._hub.pb_call(self._slave, address, count, "input")

        if raw_result is None:
            _LOGGER.info("read_inputs %s Null", self._slave)
            return None
        else:
            return raw_result.registers


class WbLightDevice (WbDevice):
    def __init__(self, hass: HomeAssistant, hub: ModbusHub, slave: int) -> None:
        super().__init__(hass, hub, slave)
        self._call_active = False
        self._states  = [False, False, False]
        self._brightnesses = [100, 100, 100]

    def supported_brightness(self, channel) -> bool:
        return True

    async def async_turn_on(self, channel: int) -> None:
        await self.async_setOnOff(channel, True)
        self._states[channel] = True

    async def async_turn_off(self, channel: int) -> None:
        await self.async_setOnOff(channel, False)
        self._states[channel] = False

    async def async_setOnOff(self, channel: int, value: bool) -> None:
        on_off_addr = self.on_off_address()
        await super().async_write_coil(on_off_addr+channel, value)

    async def async_set_brightness(self, channel:int, brightness:int) -> None:
        adjusted = round(brightness / 2.55)
        brightnesses_address = self.brightnesses_address
        await super().async_write_holding(brightnesses_address + channel, int(adjusted))

    def get_state(self, channel: int) -> bool:
        return self._states[channel]

    def get_brightness(self, channel: int) -> int:
        return round(2.55 * self._brightnesses[channel])

    def on_off_address(self):
        return 0

    async def async_update(self) -> None:
        
        if self._call_active:
            return
        try:
            self._call_active = True
    
            channles = self.channels
            on_off_address = self.on_off_address()
            state = await super().async_read_coils(on_off_address, channles)
            if (state is not None):
                for c in range(0, channles):
                    self._states[c] = state[c]


            brightnesses_address = self.brightnesses_address
            brightnesses = await super().async_read_holding(brightnesses_address, channles)
            if (brightnesses is not None):
                for c in range(0, channles):
                    self._brightnesses[c] = brightnesses[c]
        finally:
            self._call_active = False
        

class WbMdm3Device (WbLightDevice):
    def __init__(self, hass: HomeAssistant, hub: ModbusHub, slave: int) -> None:
        super().__init__(hass, hub, slave)

        modes = self.read_holding(50, 3)
        self._modes = [0,0,0]
        for c in range(0, 3):
            self._modes[c] = modes[c]

    @property
    def short_name(self) -> str:
        return "mdm3"

    @property
    def channels(self) -> str:
        return 3

    @property
    def brightnesses_address(self) -> str:
        return 0

    def supported_brightness(self, channel) -> bool:
        return self._modes[channel] != 2
