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
    def __init__(self, hass: HomeAssistant, modbus_hub: str, 
        mdm3_addresses, map6s_addresses) -> None:
        self._modbus_hub = modbus_hub
        self.mdm3s = []
        self.map6ss = []
        self.hass = hass
        self.mdm3_addresses = mdm3_addresses
        self.map6s_addresses = map6s_addresses


    def pull_data(self):
        hub = get_modbus_hub(self.hass, self._modbus_hub)
        for slave in self.mdm3_addresses:
            self.mdm3s.append(WbMdm3Device(self.hass, hub, slave))
        for slave in self.map6s_addresses:
            self.map6ss.append(WbMap6sDevice(self.hass, hub, slave))


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

        # map6s model fix
        if (model_bytes[5] == 512): 
            model_bytes[5] = 0

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


class WbMap6sDevice (WbDevice):
    def __init__(self, hass: HomeAssistant, hub: ModbusHub, slave: int) -> None:
        super().__init__(hass, hub, slave)
        self._call_active = False
        self._current = [None,None,None,None,None,None]
        self._power = [None,None,None,None,None,None]
        self._rx_power = [None,None,None,None,None,None]
        self._energy = [None,None,None,None,None,None]

    @property
    def short_name(self) -> str:
        return "map6s"
    
    async def async_update(self) -> None:
        
        if self._call_active:
            return
        try:
            self._call_active = True

            # read current (u32 big endian)
            # current addresses = [5146, 5144, 5142, 9242, 9240, 9238]  
            current_addr_5x = await super().async_read_inputs(5142, 2*3)
            current_addr_9x = await super().async_read_inputs(9238, 2*3)

            if (current_addr_5x is not None):
                self._current[0] = self.from_u32_be(current_addr_5x, 4)
                self._current[1] = self.from_u32_be(current_addr_5x, 2)
                self._current[2] = self.from_u32_be(current_addr_5x, 0)

            if (current_addr_9x is not None):
                self._current[3] = self.from_u32_be(current_addr_9x, 4)
                self._current[4] = self.from_u32_be(current_addr_9x, 2)
                self._current[5] = self.from_u32_be(current_addr_9x, 0)

            # read power (s32 big endian)
            # power addresses = [4870, 4868, 4866,  8966, 8964, 8962]
            power_addr_4x = await super().async_read_inputs(4866, 2*3)
            power_addr_8x = await super().async_read_inputs(8962, 2*3)

            if (power_addr_4x is not None):
                self._power[0] = self.from_s32_be(power_addr_4x, 4)
                self._power[1] = self.from_s32_be(power_addr_4x, 2)
                self._power[2] = self.from_s32_be(power_addr_4x, 0)

            if (power_addr_8x is not None):
                self._power[3] = self.from_s32_be(power_addr_8x, 4)
                self._power[4] = self.from_s32_be(power_addr_8x, 2)
                self._power[5] = self.from_s32_be(power_addr_8x, 0)
            
            # read rx power (s32 big endian)
            rx_power_addr_4x = await super().async_read_inputs(4874, 2*3)
            rx_power_addr_8x = await super().async_read_inputs(8970, 2*3)

            if (rx_power_addr_4x is not None):
                self._rx_power[0] = self.from_s32_be(rx_power_addr_4x, 4)
                self._rx_power[1] = self.from_s32_be(rx_power_addr_4x, 2)
                self._rx_power[2] = self.from_s32_be(rx_power_addr_4x, 0)

            if (rx_power_addr_8x is not None):
                self._rx_power[3] = self.from_s32_be(rx_power_addr_8x, 4)
                self._rx_power[4] = self.from_s32_be(rx_power_addr_8x, 2)
                self._rx_power[5] = self.from_s32_be(rx_power_addr_8x, 0)


            # read energy (u64 little endian)
            # energy addresses = [4620, 4616, 4612 ... 8716, 8712, 8708]
            energy_addr_4x = await super().async_read_inputs(4612, 4*3)
            energy_addr_8x = await super().async_read_inputs(8708, 4*3)

            if (energy_addr_4x is not None):
                self._energy[0] = self.from_u64_le(energy_addr_4x, 8)
                self._energy[1] = self.from_u64_le(energy_addr_4x, 4)
                self._energy[2] = self.from_u64_le(energy_addr_4x, 0)

            if (energy_addr_8x is not None):
                self._energy[3] = self.from_u64_le(energy_addr_8x, 8)
                self._energy[4] = self.from_u64_le(energy_addr_8x, 4)
                self._energy[5] = self.from_u64_le(energy_addr_8x, 0)

        finally:
            self._call_active = False
    
    def get_current(self, channel: int):
        return self._current[channel - 1]

    def get_power(self, channel: int):
        return self._power[channel - 1]

    def get_rx_power(self, channel: int):
        return self._rx_power[channel - 1]

    def get_energy(self, channel: int):
        return self._energy[channel - 1]


    def from_u32_be(self, array, offset) -> float:
        a = array[0 + offset]
        b = array[1 + offset]

        value = a * 65536 + b
        return value * 2.44141 / 10000000.0

    def from_s32_be(self, array, offset) -> float:
        a = array[0 + offset]
        b = array[1 + offset]

        value = 0
        if (a <= 32767):
            value = a * 65536 + b
        else:
            value = a * 65536 + b - 4294967296

        return value * 2.44141 / 10000000.0

    def from_u64_le(self, array, offset) -> float:
        a0 = array[0 + offset]
        a1 = array[1 + offset]
        a2 = array[2 + offset]
        a3 = array[3 + offset]
        total = a0 + 65536*a1 + 4294967296 * a2 + 281474976710656 * a3
        total = total * 0.00001

        return total