""" 
This file is licensed under the MIT License.
See the LICENSE file in the root directory for full license text.

Copyright (c) 2025 OmniBuds Ltd

Author: Yang Liu  
Email: yang.liu3e@gmail.com  

"""

import time
import asyncio
import logging
from .base import BaseSensorCommand
from .ids import PeripheralID, MsgID, MsgType
from .ids import SensorConfig as SC

logger = logging.getLogger(__name__)


# ============================
# Motion Sensor Configuration
# ============================


class AccelerometerCommand(BaseSensorCommand):
    """Configure the accelerometer sensor (e.g., sampling rate, scale, filters)."""

    PERIPHERAL_ID = PeripheralID.ACC
    CONFIG = {
        "enable": 0,
        "sampling_rate": 1,
        "scale_range": 2,
    }


class GyroCommand(BaseSensorCommand):
    """Configure the gyroscope sensor."""

    PERIPHERAL_ID = PeripheralID.GYRO
    CONFIG = AccelerometerCommand.CONFIG  # Reuse the same structure


class MagnetometerCommand(BaseSensorCommand):
    """Configure the magnetometer sensor."""

    PERIPHERAL_ID = PeripheralID.MAG
    CONFIG = {
        "enable": 0,
        "sampling_rate": 1,
    }


# ============================
# Optical & Bio-signal Sensors
# ============================


class PPGRawCommand(BaseSensorCommand):
    """Configure raw PPG sensor settings (e.g., sampling, LED current)."""

    PERIPHERAL_ID = PeripheralID.PPG_RAW
    CONFIG = {
        "enable": 0,
        "sampling_rate": 1,
        "led_current": 2,
    }


class HeartRateCommand(BaseSensorCommand):
    """Enable or disable heart rate monitoring."""

    PERIPHERAL_ID = PeripheralID.HR
    CONFIG = {
        "enable": 0,
        "periodicity": 1,
    }


class HRVCommand(BaseSensorCommand):
    """Enable or disable heart rate variability (HRV) measurement."""

    PERIPHERAL_ID = PeripheralID.HRV
    CONFIG = {
        "enable": 0,
    }


class SpO2Command(BaseSensorCommand):
    """Enable or disable SpO2 (blood oxygen saturation) measurement."""

    PERIPHERAL_ID = PeripheralID.SPO2
    CONFIG = {
        "enable": 0,
    }


class RespirationRateCommand(BaseSensorCommand):
    """Enable or disable respiration rate measurement."""

    PERIPHERAL_ID = PeripheralID.RESP_RATE
    CONFIG = {
        "enable": 0,
    }


# ============================
# Temperature Sensors
# ============================



class TempObjectCommand(BaseSensorCommand):
    """Control object temperature sensor."""

    PERIPHERAL_ID = PeripheralID.TEMP_OBJ
    CONFIG = {
        "enable": 0,
        "periodicity": 1,
    }


# ============================
# System and Utility Commands
# ============================


class TimestepUpdateCommand(BaseSensorCommand):
    """Push the host's current time to the device for synchronization."""

    PERIPHERAL_ID = PeripheralID.GET_CURRENT_TIME
    CONFIG = {"enable": 0}

    async def send_time_response(self, CHAR_UUID):
        """Send current Unix timestamp (in ms) to device."""
        unix_time = time.time()
        ms_timestamp = f"{int(unix_time * 1000)}"
        try:
            await self.send_command(
                CHAR_UUID=CHAR_UUID,
                message_type=MsgType.WRITE,
                message_id=MsgID.CONFIG_MSG,
                endpoint=self.CONFIG["enable"],
                error_code=0,
                data=ms_timestamp,
                is_response=True,
            )
            logger.debug(f"Sent current timestamp: {ms_timestamp}")
        except asyncio.CancelledError:
            logger.warning("Task was cancelled before write could complete.")


class PowerManagementCommand(BaseSensorCommand):
    """Configure power management features (e.g., load balancing)."""

    PERIPHERAL_ID = PeripheralID.POWER_MANAGEMENT
    CONFIG = {
        "load_balancing": 0,
        "peripheral_control": 1,
    }

    async def disable_all_sensors(self, CHAR_UUID):
        """Disable all sensor peripherals."""
        await self.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=self.CONFIG["peripheral_control"],
            data=SC.SensorToggle.DISABLE,
        )

    async def disable_power_optimization(self, CHAR_UUID):
        """Disable on-device power optimization (e.g., load balancing)."""
        await self.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=self.CONFIG["load_balancing"],
            data=SC.SensorToggle.DISABLE,
        )

    async def enable_power_optimization(self, CHAR_UUID):
        """Enable on-device power optimization (e.g., load balancing)."""
        await self.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=self.CONFIG["load_balancing"],
            data=SC.SensorToggle.ENABLE,
        )


class FirmwareVersionCommand(BaseSensorCommand):
    """Request firmware version information."""

    PERIPHERAL_ID = PeripheralID.OMNIBUD_FIRMWARE_VERSION


# ============================
# Event Detection Commands
# ============================


class ButtonPressDetectionCommand(BaseSensorCommand):
    """Detect physical button press events."""

    PERIPHERAL_ID = PeripheralID.BUTTON_PRESS
    CONFIG = {
        "enable": 0,
    }


class InEarDectetionCommand(BaseSensorCommand):
    """Detect whether the earbuds are in-ear or out-of-ear."""

    PERIPHERAL_ID = PeripheralID.IN_EAR
    CONFIG = {
        "enable": 0,
    }


class EarbudsSleepCommand(BaseSensorCommand):
    """Control or report sleep mode status of the earbuds."""

    PERIPHERAL_ID = PeripheralID.OMNIBUD_SLEEP
