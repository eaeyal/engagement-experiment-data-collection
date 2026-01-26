""" 
This file is licensed under the MIT License.
See the LICENSE file in the root directory for full license text.

Copyright (c) 2025 OmniBuds Ltd

Author: Yang Liu  
Email: yang.liu3e@gmail.com  

"""

import logging
from .ids import PeripheralID, MsgID, MsgType, OmniBudsUUID

logger = logging.getLogger(__name__)


class BaseSensorCommand:
    """
    Base class for sending BLE sensor configuration and control commands.
    Each subclass should define a PERIPHERAL_ID and optional CONFIG dictionary.
    """

    PERIPHERAL_ID = None  # Must be overridden in subclasses

    def __init__(self, client=None, manager=None):
        """
        Args:
            client: BLE client (e.g., bleak.BleakClient)
            manager: Optional manager to coordinate response waits
        """
        self.peripheral_id = self.PERIPHERAL_ID
        self.client = client
        self.manager = manager

    def construct_packet(
        self,
        peripheral_id: PeripheralID = None,
        message_id: MsgID = MsgID.CONFIG_MSG,
        message_type: MsgType = MsgType.WRITE,
        endpoint: int = 0,
        data: list = [],
        is_response: bool = False,
        error_code: int = 0,
    ) -> bytearray:
        """
        Constructs a BLE packet for command or response message.

        Args:
            peripheral_id (PeripheralID): Target sensor.
            message_id (MsgID): CONFIG_MSG, DATA_MSG, EVENTS_MSG.
            message_type (MsgType): READ, WRITE, READ_RESP, WRITE_RESP.
            endpoint (int): Endpoint ID defined per peripheral.
            data (list|str): Data payload (will be ASCII-encoded if str).
            is_response (bool): Whether packet is a response (adds error_code).
            error_code (int): Only used for responses.

        Returns:
            bytearray: Encoded BLE message.
        """
        pid = peripheral_id or self.peripheral_id
        if pid is None:
            raise ValueError("peripheral_id must be provided.")

        # Normalize payload
        if isinstance(data, str):
            data = [ord(c) for c in data]
        elif not isinstance(data, list):
            raise TypeError("data must be a list or string.")

        # Header byte structure: [5 bits reserved][2 bits type][3 bits msg ID]
        reserved = 0
        mtype = message_type.value & 0x03
        mid = message_id.value & 0x07
        header_byte = (reserved << 5) | (mtype << 3) | mid

        misc = 0  # Reserved field (may encode sensor settings)
        checksum = 0  # Placeholder (could be used for XOR checksum)

        # Construct payload based on whether this is a response
        if is_response:
            payload = [endpoint, error_code] + data
        else:
            payload = [endpoint] + data

        data_length = len(payload)

        # Full packet structure:
        # [peripheral_id][header][length][misc][checksum][payload...]
        packet = bytearray(
            [
                pid,  # Peripheral ID
                header_byte,  # Encodes MsgType & MsgID
                data_length,  # Payload length
                misc,  # Reserved
                checksum,  # Optional checksum (default 0)
            ]
            + payload
        )

        return packet

    async def send_command(
        self,
        CHAR_UUID: str = OmniBudsUUID.CHAR_UUID_RIGHT,
        peripheral_id: PeripheralID = None,
        message_id: MsgID = MsgID.CONFIG_MSG,
        message_type: MsgType = MsgType.WRITE,
        endpoint: int = 0,
        data: list = [],
        is_response: bool = False,
        error_code: int = 0,
    ):
        """
        Sends a constructed BLE command packet to the OmniBuds device.

        Args:
            CHAR_UUID (str): BLE GATT characteristic UUID.
            peripheral_id (PeripheralID): Target sensor or subsystem.
            message_id (MsgID): Type of message.
            message_type (MsgType): WRITE, READ, or their RESP variants.
            endpoint (int): Command endpoint for the peripheral.
            data (list|str): Payload (int list or ASCII string).
            is_response (bool): Whether this is a response-type message.
            error_code (int): Optional error code (for response messages).

        Returns:
            bytearray: Sent packet.
        """
        peripheral_id = peripheral_id or self.peripheral_id
        if peripheral_id is None:
            raise ValueError("peripheral_id must be provided.")

        packet = self.construct_packet(
            peripheral_id=peripheral_id,
            message_id=message_id,
            message_type=message_type,
            endpoint=endpoint,
            data=data,
            is_response=is_response,
            error_code=error_code,
        )

        hex_str = " ".join(f"{b:02X}" for b in packet)

        # Log debug output
        logger.debug(f"[HEX]  → {hex_str}")
        logger.debug(
            f"[SEND] → Peripheral: {peripheral_id.name}, "
            f"MsgID: {message_id.name}, Type: {message_type.name}, "
            f"Endpoint: {endpoint}, Error: {error_code if is_response else '-'}, "
            f"Data: {data}"
        )

        # Send via BLE
        if self.client:
            await self.client.write_gatt_char(CHAR_UUID, bytes(packet))
        else:
            logger.warning(
                f"BLE client is not set. Packet constructed but not sent.\n"
                f"Packet content: {hex_str}\n"
                f"To send: cmd = {self.__class__.__name__}(client=your_ble_client)"
            )

        # Optional wait for response if manager exists
        if self.manager:
            await self.manager.wait_for_config_response(peripheral_id.value, endpoint)

        return packet

    def print_endpoint(self):
        """
        Print available endpoint names and values defined in the CONFIG dictionary.
        Useful for developers when interacting with commands manually.
        """
        logger.info(f"[{self.__class__.__name__}] Supported CONFIG endpoints:")
        for name, eid in getattr(self, "CONFIG", {}).items():
            logger.info(f"  - {name}: endpoint = {eid}")
