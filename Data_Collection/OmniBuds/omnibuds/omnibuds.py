""" 
This file is licensed under the MIT License.
See the LICENSE file in the root directory for full license text.

Copyright (c) 2025 OmniBuds Ltd

Author: Yang Liu  
Email: yang.liu3e@gmail.com  

"""

import asyncio
import logging
import omnibuds.com as com
from omnibuds.base import BaseSensorCommand
from .ids import PeripheralID, MsgID, MsgType, OmniBudsUUID
from .ids import SensorConfig as SC

logger = logging.getLogger(__name__)


class OmniBudsCommand:
    """
    Registry and factory for OmniBuds sensor command classes.
    Automatically registers all subclasses of BaseSensorCommand from the omnibuds.com module.
    """

    _client = None
    _manager = None
    _registry = {}

    @classmethod
    def init(cls, client, manager):
        """Initialize the command system with BLE client and optional config manager."""
        cls._client = client
        cls._manager = manager

        for name in dir(com):
            obj = getattr(com, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseSensorCommand)
                and obj is not BaseSensorCommand
            ):
                key = name.replace("Command", "")
                cls._registry[key] = obj
                logger.debug(f"[REGISTERED] {key} → {obj.__name__}")

    @classmethod
    def get(cls, name) -> BaseSensorCommand:
        """Get an instance of a registered command class by name."""
        if name not in cls._registry:
            raise ValueError(f"No command registered with name: {name}")
        return cls._registry[name](cls._client, cls._manager)

    @classmethod
    def all(cls, verbose=True):
        """Return all registered commands as instances."""
        result = {}
        for name, cmd_class in cls._registry.items():
            instance = cmd_class(cls._client, cls._manager)
            result[name] = instance
            if verbose:
                docstring = (cmd_class.__doc__ or "").strip()
                doc = docstring.splitlines()[0] if docstring else "No description"
                logger.info(f"{name:<20}  -  {doc}")
        return result


class OmniBudsComManager:
    """
    BLE communication manager that handles notifications, ACK events,
    and provides time sync and response waiting utilities.
    """

    def __init__(self, client):
        self.client = client
        self.pending_events = {}
        self.OmniBudsUUID = OmniBudsUUID
        self.loop = asyncio.get_event_loop()
        self._notification_active = True
        self.timeupdated = False

    def disable_notifications(self):
        """Temporarily disable notification handler dispatch."""
        self._notification_active = False

    def enable_notifications(self):
        """Re-enable notification dispatching."""
        self._notification_active = True

    def _default_notification_handler(self, sender, data):
        """No-op default handler."""
        pass

    def build_omnibuds_handler(self, user_handler=None):
        """Create a BLE notification handler function for OmniBuds packets."""
        self._notification_active = True

        def handler(sender, data):
            if not self._notification_active:
                return
            try:
                parsed = OmniBudsParsedPacket(data)
                logger.debug(parsed)

                # Respond to GET_CURRENT_TIME config request
                if (
                    parsed.is_config_request
                    and parsed.endpoint == 0
                    and self.timeupdated == False
                    and parsed.peripheral_id == PeripheralID.GET_CURRENT_TIME
                ):
                    self.timeupdated = True
                    time_cmd = com.TimestepUpdateCommand(self.client)
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(time_cmd.send_time_response(sender))
                    )

                # Match pending config responses and resolve awaiting event
                if parsed.is_config_response:
                    key = (parsed.peripheral_id, parsed.endpoint)
                    event = self.pending_events.get(key)
                    fallback_key = (-1, -1)
                    if not event:
                        event = self.pending_events.get(fallback_key)
                    if event:
                        event.set()
                        if parsed.error_code != 0:
                            logger.warning(
                                f"[ACK] → Config response failed with error code: {parsed.error_code}"
                            )

            except Exception as e:
                logger.warning(f"Failed to parse notification data: {e}")

            if user_handler:
                user_handler(sender, data)

        return handler

    async def wait_for_config_response(self, peripheral_id=-1, endpoint=-1, timeout=2):
        """
        Await a config response for a given peripheral and endpoint.

        Args:
            peripheral_id (int): Target peripheral ID.
            endpoint (int): Target endpoint.
            timeout (int): Timeout in seconds.
        """
        key = (peripheral_id, endpoint)
        event = asyncio.Event()
        self.pending_events[key] = event

        try:
            await asyncio.wait_for(event.wait(), timeout)
            logger.debug(
                f"[ACK] → Received config response for {key}"
                if key != (-1, -1)
                else "[ACK] → Received config response"
            )
        except asyncio.TimeoutError:
            msg = (
                f"[ACK] → Timeout waiting for config response on {key}"
                if key != (-1, -1)
                else "[ACK] → Timeout waiting for config response"
            )
            logger.debug(msg)
        finally:
            self.pending_events.pop(key, None)


class OmniBudsUtils:
    """
    Utility helper class providing battery status and service UUID inspection.
    """

    def __init__(self, client):
        self.client = client
        self.battery_reader = OmniBudsBatteryReader(client)

    async def get_battery_levels(self):
        """Get battery levels for left and right earbuds."""
        return await self.battery_reader.read_battery_levels()

    def battery_status_str(self):
        """Return battery level summary string."""
        return str(self.battery_reader)

    async def print_all_service_uuids(self):
        """Print all discovered GATT service and characteristic UUIDs."""
        logger.info("\n📱 Connected Services and UUID Map:\n")

        for service in self.client.services:
            logger.info(f"🔧 Service: {service.uuid}")
            for char in service.characteristics:
                props = ", ".join(char.properties)
                logger.info(
                    f"  └︎🔸 Characteristic: {char.uuid} (Properties: {props}, Handle: {char.handle})"
                )

                if char.descriptors:
                    for desc in char.descriptors:
                        logger.info(
                            f"     └︎🖍️ Descriptor: {desc.uuid} (Handle: {desc.handle})"
                        )

        logger.info("\n✅ UUID scan complete.\n")


class OmniBudsParsedPacket:
    def __init__(self, raw_packet: bytes):
        if len(raw_packet) < 6:
            raise ValueError("Packet too short to parse.")

        self.raw = bytes(raw_packet)
        logger.debug(f"[RECV] → {' '.join(f'{b:02X}' for b in self.raw)}")

        self.peripheral_id = self.raw[0]
        try:
            self.peripheral_id_name = PeripheralID(self.peripheral_id)
            self.id_name = self.peripheral_id_name.name
        except ValueError:
            self.peripheral_id_name = f"Unknown (0x{self.peripheral_id:02X})"
            self.id_name = self.peripheral_id_name

        header_byte = self.raw[1]
        self.reserved = (header_byte >> 5) & 0x07
        self.message_type = MsgType((header_byte >> 3) & 0x03)
        self.message_id = MsgID(header_byte & 0x07)

        self.data_length = self.raw[2]
        self.misc = self.raw[3]
        self.checksum = self.raw[4]

        self.endpoint = None
        self.error_code = None
        self.config_data = None

        self.is_config_response = (
            self.message_id == MsgID.CONFIG_MSG
            and self.message_type in (MsgType.READ_RESP, MsgType.WRITE_RESP)
        )

        self.is_config_request = (
            self.message_id == MsgID.CONFIG_MSG
            and self.message_type in (MsgType.READ, MsgType.WRITE)
        )

        self.is_data_message = (
            self.message_id == MsgID.DATA_MSG
            and self.message_type in (MsgType.READ, MsgType.WRITE)
        )

        self.is_event_message = self.message_id == MsgID.EVENTS_MSG
    

        logger.debug(
            f"[RECV FLAGS] → is_config_request: {self.is_config_request}, "
            f"is_config_response: {self.is_config_response}, "
            f"is_data_message: {self.is_data_message},"
            f"is_event_message: {self.is_event_message}"
        )
        logger.debug(
            f"[RECV META] → MsgID: {self.message_id.name}, MsgType: {self.message_type.name}"
        )

        if self.is_config_response:
            self.endpoint = self.raw[5]
            self.error_code = self.raw[6]
            self.config_data = self.raw[7 : 7 + (self.data_length)]

        elif self.is_config_request:
            self.endpoint = self.raw[5]
            self.config_data = self.raw[6 : 6 + (self.data_length)]

        elif self.is_data_message or self.is_event_message:
            self.data_payload = self.raw[5 : 5 + self.data_length]
        else:
            return logger.error("Unrecognized or unsupported message format.")

    def get_ppg_samples(self):
        """
        Parse PPG_RAW payload into timestamped samples (Green, Red, IR).

        Returns:
            List[Tuple[int, str, str, str]]: Each tuple contains (timestamp, green, red, ir).
        """
        if self.peripheral_id != PeripheralID.PPG_RAW or not self.data_payload:
            logger.warning("get_ppg_samples called on non-PPG_RAW packet.")
            return []

        # Convert bytes to readable ASCII string
        payload_str = "".join(chr(b) for b in self.data_payload if 32 <= b <= 126)
        if not payload_str:
            return []

        try:
            sampling_rate = int(self.misc)
        except ValueError:
            logger.error(f"Invalid sampling rate in misc_value: {self.misc}")
            return []

        sample_interval = 1000 // sampling_rate  # in milliseconds
        parts = payload_str.split(",")

        try:
            base_timestamp = int(parts[0])
        except ValueError:
            logger.error(f"Invalid base timestamp in payload: {parts[0]}")
            return []

        samples = parts[1:]
        parsed_samples = []

        # Group every three samples as (green, red, ir)
        for i in range(0, len(samples), 3):
            if i + 2 < len(samples):
                timestamp = base_timestamp + (i // 3) * sample_interval
                parsed_samples.append(
                    (timestamp, samples[i], samples[i + 1], samples[i + 2])
                )

        return parsed_samples

    def get_acc_samples(self):
        """
        Parses ACC data into timestamped (x, y, z) acceleration values in g.

        Returns:
            List of tuples: [(timestamp, x_g, y_g, z_g), ...]
        """
        if self.peripheral_id != PeripheralID.ACC or not hasattr(self, "data_payload"):
            logger.warning("get_acc_samples called on non-ACC packet.")
            return []

        payload_str = "".join(chr(b) for b in self.data_payload if 32 <= b <= 126)
        if not payload_str:
            return []

        try:
            misc = int(self.misc)
            rate = (misc >> 4) & 0x0F
            sensor_range = str(misc & 0x0F)
            sample_interval = 1000 // SC.Accel.SamplingRate.to_hz(str(rate))
        except Exception as e:
            logger.error(f"Failed to decode ACC misc value: {self.misc}")
            return []

        parts = payload_str.rstrip(",").split(",")
        try:
            base_timestamp = int(parts[0])
        except:
            logger.error("Invalid base timestamp in ACC payload.")
            return []

        samples = parts[1:]
        result = []

        for i in range(0, len(samples), 3):
            if i + 2 < len(samples):
                try:
                    x = SC.Accel.lsb_to_g(int(samples[i]), sensor_range)
                    y = SC.Accel.lsb_to_g(int(samples[i + 1]), sensor_range)
                    z = SC.Accel.lsb_to_g(int(samples[i + 2]), sensor_range)
                    ts = base_timestamp + (i // 3) * sample_interval
                    result.append((ts, f"{x:.4f}", f"{y:.4f}", f"{z:.4f}"))
                except Exception:
                    continue
        return result

    def get_gyro_samples(self):
        """
        Parses GYRO data into timestamped (x, y, z) angular velocity in dps.

        Returns:
            List of tuples: [(timestamp, x_dps, y_dps, z_dps), ...]
        """
        if self.peripheral_id != PeripheralID.GYRO or not hasattr(self, "data_payload"):
            logger.warning("get_gyro_samples called on non-GYRO packet.")
            return []

        payload_str = "".join(chr(b) for b in self.data_payload if 32 <= b <= 126)
        if not payload_str:
            return []

        try:
            misc = int(self.misc)
            rate = (misc >> 4) & 0x0F
            sensor_range = str(misc & 0x0F)
            sample_interval = 1000 // SC.Gyro.SamplingRate.to_hz(str(rate))
        except Exception:
            logger.error(f"Failed to decode GYRO misc value: {self.misc}")
            return []

        parts = payload_str.rstrip(",").split(",")
        try:
            base_timestamp = int(parts[0])
        except:
            logger.error("Invalid base timestamp in GYRO payload.")
            return []

        samples = parts[1:]
        result = []

        for i in range(0, len(samples), 3):
            if i + 2 < len(samples):
                try:
                    x = SC.Gyro.lsb_to_dps(int(samples[i]), sensor_range)
                    y = SC.Gyro.lsb_to_dps(int(samples[i + 1]), sensor_range)
                    z = SC.Gyro.lsb_to_dps(int(samples[i + 2]), sensor_range)
                    ts = base_timestamp + (i // 3) * sample_interval
                    result.append((ts, f"{x:.4f}", f"{y:.4f}", f"{z:.4f}"))
                except Exception:
                    continue
        return result

    def get_mag_samples(self):
        """
        Parses MAG data into timestamped (x, y, z) magnetic field in Gauss.

        Returns:
            List of tuples: [(timestamp, x_gauss, y_gauss, z_gauss), ...]
        """
        if self.peripheral_id != PeripheralID.MAG or not hasattr(self, "data_payload"):
            logger.warning("get_mag_samples called on non-MAG packet.")
            return []

        payload_str = "".join(chr(b) for b in self.data_payload if 32 <= b <= 126)
        if not payload_str:
            return []

        try:
            misc = int(self.misc)
            rate = (misc >> 4) & 0x0F
            sample_interval = 1000 // SC.Mag.SamplingRate.to_hz(str(rate))
        except Exception:
            logger.error(f"Failed to decode MAG misc value: {self.misc}")
            return []

        parts = payload_str.rstrip(",").split(",")
        try:
            base_timestamp = int(parts[0])
        except:
            logger.error("Invalid base timestamp in MAG payload.")
            return []

        samples = parts[1:]
        result = []

        for i in range(0, len(samples), 3):
            if i + 2 < len(samples):
                try:
                    x = SC.Mag.lsb_to_gauss(int(samples[i]))
                    y = SC.Mag.lsb_to_gauss(int(samples[i + 1]))
                    z = SC.Mag.lsb_to_gauss(int(samples[i + 2]))
                    ts = base_timestamp + (i // 3) * sample_interval
                    result.append((ts, f"{x:.4f}", f"{y:.4f}", f"{z:.4f}"))
                except Exception:
                    continue
        return result

    def get_other_samples(self):
        """
        Parses single-value sensor packets (TEMP, HR, SpO2, etc.) into (timestamp, value).

        Returns:
            List of tuples: [(timestamp, value_str)]
        """
        known_simple_ids = {
            PeripheralID.TEMP_OBJ,
            PeripheralID.HR,
            PeripheralID.HRV,
            PeripheralID.SPO2,
            PeripheralID.RESP_RATE,
            PeripheralID.BUTTON_PRESS,
            PeripheralID.IN_EAR,
            PeripheralID.OMNIBUD_SLEEP,
            PeripheralID.GET_CURRENT_TIME,
            PeripheralID.POWER_MANAGEMENT,
            PeripheralID.OMNIBUD_FIRMWARE_VERSION,
        }

        if self.peripheral_id not in known_simple_ids or not hasattr(
            self, "data_payload"
        ):
            logger.warning(
                "get_other_samples called on unsupported or malformed packet."
            )
            return []

        # Convert payload to ASCII string
        payload_str = "".join(chr(b) for b in self.data_payload if 32 <= b <= 126)
        if not payload_str:
            logger.warning("Payload string is empty or non-decodable.")
            return []

        parts = payload_str.rstrip(",").split(",")
        if len(parts) < 2:
            logger.error("Payload does not contain both timestamp and value.")
            return []

        try:
            timestamp = int(parts[0])
            value = parts[1].strip()
            return [(timestamp, value)]
        except Exception as e:
            logger.error(f"Failed to parse timestamp/value: {e}")
            return []

    def get_samples(self):
        """
        Automatically dispatches to the appropriate sample parser based on peripheral_id.

        Returns:
            List of tuples: [(timestamp, x, y, z or green, red, ir or value), ...]
        """
        if not getattr(self, "is_data_message", False):
            logger.warning("get_samples called on non-data message packet.")
            return []

        if self.peripheral_id == PeripheralID.PPG_RAW:
            return self.get_ppg_samples()
        elif self.peripheral_id == PeripheralID.ACC:
            return self.get_acc_samples()
        elif self.peripheral_id == PeripheralID.GYRO:
            return self.get_gyro_samples()
        elif self.peripheral_id == PeripheralID.MAG:
            return self.get_mag_samples()
        elif self.peripheral_id in {
            PeripheralID.TEMP_OBJ,
            PeripheralID.HR,
            PeripheralID.HRV,
            PeripheralID.SPO2,
            PeripheralID.RESP_RATE,
            PeripheralID.BUTTON_PRESS,
            PeripheralID.IN_EAR,
            PeripheralID.OMNIBUD_SLEEP,
            PeripheralID.GET_CURRENT_TIME,
            PeripheralID.POWER_MANAGEMENT,
            PeripheralID.OMNIBUD_FIRMWARE_VERSION,
        }:
            return self.get_other_samples()
        else:
            logger.warning(
                f"No sample parser defined for peripheral_id: {self.peripheral_id}"
            )
            return []

    def __str__(self):
        base = (
            f"Peripheral ID     : {self.peripheral_id} ({self.id_name})\n"
            f"Message ID        : {self.message_id.name}\n"
            f"Message Type      : {self.message_type.name}\n"
            f"Reserved Bits     : {self.reserved}\n"
            f"Data Length       : {self.data_length}\n"
            f"Misc              : {self.misc}\n"
            f"Checksum          : 0x{self.checksum:02X}\n"
        )
        if self.is_config_response:
            config = (
                f"Config Endpoint   : {self.endpoint}\n"
                f"Error Code        : {self.error_code}\n"
                f"Config Data (hex) : {' '.join(f'{b:02X}' for b in self.config_data)}\n"
                f"Config Data (str) : {''.join(chr(b) for b in self.config_data if 32 <= b <= 126)}"
            )
            return f"\n{'-'*60}\n" + base + config + f"\n{'-'*60}"
        elif self.is_config_request:
            config = (
                f"Config Endpoint   : {self.endpoint}\n"
                f"Config Data (hex) : {' '.join(f'{b:02X}' for b in self.config_data)}\n"
                f"Config Data (str) : {''.join(chr(b) for b in self.config_data if 32 <= b <= 126)}"
            )
            return f"\n{'-'*60}\n" + base + config + f"\n{'-'*60}"
        elif self.is_data_message or self.is_event_message:
            data_str = (
                f"Data Payload (hex): {' '.join(f'{b:02X}' for b in self.data_payload)}\n"
                f"Data Payload (str): {''.join(chr(b) for b in self.data_payload if 32 <= b <= 126)}"
            )
            return f"\n{'-'*60}\n" + base + data_str + f"\n{'-'*60}"

        else:
            return base + "Unrecognized or unsupported message format."


class OmniBudsBatteryReader:
    """
    Utility class to read battery levels from left and right OmniBuds.

    It scans the GATT services for battery-related characteristics and uses descriptor
    UUIDs to determine whether the battery percentage belongs to the left or right earbud.
    """

    def __init__(self, client):
        """
        Args:
            client: An active BLE client (e.g., bleak.BleakClient).
        """
        self.client = client
        self.battery_levels = {}  # Dict with keys "left" and "right"
        self.temp_handles = []  # Optional placeholder if handle tracking is needed

    async def read_battery_levels(self) -> dict:
        """
        Reads battery levels from all available battery characteristics.

        Returns:
            dict: { "left": <percent>, "right": <percent> }
        """
        self.battery_levels = {}
        services = self.client.services

        for service in services:
            if service.uuid.lower() == OmniBudsUUID.BATTERY_SERVICE_UUID:
                for char in service.characteristics:
                    if "read" not in char.properties:
                        continue

                    # Attempt to read battery percentage from characteristic
                    try:
                        battery_value = await self.client.read_gatt_char(char.handle)
                        if battery_value and len(battery_value) > 0:
                            battery_percent = int(battery_value[0])
                        else:
                            logger.warning(
                                f"Empty battery value from handle {char.handle}"
                            )
                            continue
                    except Exception as e:
                        logger.warning(
                            f"Failed to read battery level from handle {char.handle}: {e}"
                        )
                        continue

                    # Use descriptors to identify left/right earbud
                    ear_found = False
                    for desc in char.descriptors:
                        if desc.uuid.lower() == OmniBudsUUID.BATTERY_DESCRIPTION_UUID:
                            try:
                                value = await self.client.read_gatt_descriptor(
                                    desc.handle
                                )
                                desc_bytes = value[5:7]

                                # Left earbud: b'\x0d\x01', Right earbud: b'\x0e\x01'
                                if desc_bytes == b"\x0d\x01":
                                    self.battery_levels["left"] = battery_percent
                                    ear_found = True
                                elif desc_bytes == b"\x0e\x01":
                                    self.battery_levels["right"] = battery_percent
                                    ear_found = True
                            except Exception as e:
                                logger.error(
                                    f"Failed to read descriptor at handle {desc.handle}: {e}"
                                )

                    if not ear_found:
                        logger.info(
                            f"No valid 0x2904 descriptor found for handle {char.handle}. "
                            f"Cannot assign battery value to left or right ear."
                        )

        return self.battery_levels

    def __str__(self):
        """
        Returns a human-readable battery level summary string.
        """
        left = self.battery_levels.get("left", "N/A")
        right = self.battery_levels.get("right", "N/A")
        result = [
            f"Left Earbud Battery : {left}%",
            f"Right Earbud Battery: {right}%",
        ]
        return "\n".join(result)
