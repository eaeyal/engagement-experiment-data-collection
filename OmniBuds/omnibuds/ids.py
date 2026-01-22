""" 
This file is licensed under the MIT License.
See the LICENSE file in the root directory for full license text.

Copyright (c) 2025 OmniBuds Ltd

Author: Yang Liu  
Email: yang.liu3e@gmail.com  

"""

from enum import Enum, StrEnum, IntEnum


from enum import Enum, IntEnum

# ============================
# Peripheral Identifiers
# ============================


class PeripheralID(IntEnum):
    ACC = 0                             # Accelerometer
    GYRO = 1                            # Gyroscope
    MAG = 2                             # Magnetometer
    PPG_RAW = 5                         # Raw PPG sensor
    TEMP_OBJ = 7                        # Object temperature sensor
    HR = 9                              # Heart rate monitor
    HRV = 10                            # Heart rate variability
    SPO2 = 11                           # Blood oxygen level (SpO2)
    RESP_RATE = 12                      # Respiration rate monitor
    BUTTON_PRESS = 28                   # Physical button press detection
    IN_EAR = 30                         # In-ear detection (wearing status)
    OMNIBUD_SLEEP = 34                  # Trigger OmniBuds sleep mode
    GET_CURRENT_TIME = 35               # Push current time to device
    POWER_MANAGEMENT = 36               # Power management features
    OMNIBUD_FIRMWARE_VERSION = 41       # Get firmware version of OmniBuds


# ============================
# Message Identifiers
# ============================


class MsgID(Enum):
    EVENTS_MSG = 0  # Event-related message
    CONFIG_MSG = 1  # Configuration command or response
    DATA_MSG = 2  # Sensor data packet


# ============================
# Message Types
# ============================


class MsgType(Enum):
    READ = 0  # Read request
    WRITE = 1  # Write command
    READ_RESP = 2  # Response to a read
    WRITE_RESP = 3  # Response to a write


# ============================
# Error Codes
# ============================


class MsgErrorCode(Enum):
    SUCCESS = 0  # Operation succeeded
    FAILED = 1  # Operation failed


class OmniBudsUUID:
    """
    UUIDs related to BLE communication with OmniBuds.
    Characteristic UUIDs are separated for left and right earbuds.
    """

    # Characteristic UUIDs
    CHAR_UUID_LEFT = (
        "00000a01-ae4a-11ed-afa1-0242ac120002"  # Characteristic for Left OmniBud
    )
    CHAR_UUID_RIGHT = (
        "00000a02-ae4a-11ed-afa1-0242ac120002"  # Characteristic for Right OmniBud
    )
    BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
    BATTERY_DESCRIPTION_UUID = "00002904-0000-1000-8000-00805f9b34fb"

    # Add more UUIDs for other characteristics or sensors as needed


class Periodicity(StrEnum):
    """
    Common periodicity for low-rate sensors.
    """

    EVERY_SECOND = "0"
    EVERY_30S = "1"
    EVERY_MINUTE = "2"
    EVERY_12S = "3"  # Only used by BP


class SensorConfig:
    class SensorToggle(StrEnum):
        """
        Common enable/disable command used across all sensors.
        Will be encoded using ASCII (e.g., "1" -> 49).
        """

        DISABLE = "0"  # ASCII 48
        ENABLE = "1"  # ASCII 49

    class Accel:
        """
        Accelerometer configuration.
        """

        class Scale(StrEnum):
            SCALE_2G = "0"
            SCALE_4G = "1"
            SCALE_8G = "2"
            SCALE_16G = "3"

            @classmethod
            def to_g(cls, value):
                """
                Convert a Scale enum value or string to its corresponding G setting.

                Examples:
                    Accel.Scale.to_g(Accel.Scale.SCALE_4G)      # returns 4
                    Accel.Scale.to_g("2")                       # returns 8
                    Accel.Scale.to_g(Accel.Scale.SCALE_16G)     # returns 16
                """
                _scale_g_map = {
                    "0": 2,
                    "1": 4,
                    "2": 8,
                    "3": 16,
                }

                if isinstance(value, cls):
                    key = value.value
                elif isinstance(value, str):
                    key = value
                else:
                    raise ValueError(f"Cannot convert {value!r} to G for Accel.Scale")
                return _scale_g_map[key]

        class SamplingRate(StrEnum):
            RATE_12HZ = "0"
            RATE_25HZ = "1"
            RATE_50HZ = "2"
            RATE_100HZ = "3"

            @classmethod
            def to_hz(cls, value):
                """
                Convert a SamplingRate enum value or string to its corresponding Hz setting.

                Examples:
                    Accel.SamplingRate.to_hz(Accel.SamplingRate.RATE_25HZ)   # returns 25
                    Accel.SamplingRate.to_hz("3")                            # returns 100
                    Accel.SamplingRate.to_hz(Accel.SamplingRate.RATE_12HZ) # returns 12.5
                """
                _rate_hz_map = {
                    "0": 12,
                    "1": 25,
                    "2": 50,
                    "3": 100,
                }

                if isinstance(value, cls):
                    key = value.value
                elif isinstance(value, str):
                    key = value
                else:
                    raise ValueError(
                        f"Cannot convert {value!r} to Hz for Accel.SamplingRate"
                    )
                return _rate_hz_map[key]

        @staticmethod
        def lsb_to_g(lsb: int, scale: "SensorConfig.Accel.Scale") -> float:
            """
            Convert raw sensor integer value (lsb) to g (g) based on the scale.

            Args:
                lsb (int): Raw sensor value (int16_t from device)
                scale (Accel.Scale or str): Measurement scale (2G, 4G, 8G, 16G)

            Returns:
                float: Value in milli-g (mg)

            Conversion factors:
                2G  -> 0.061 mg/LSB
                4G  -> 0.122 mg/LSB
                8G  -> 0.244 mg/LSB
                16G -> 0.488 mg/LSB
            """
            scale_map = {
                SensorConfig.Accel.Scale.SCALE_2G: 0.061,
                SensorConfig.Accel.Scale.SCALE_4G: 0.122,
                SensorConfig.Accel.Scale.SCALE_8G: 0.244,
                SensorConfig.Accel.Scale.SCALE_16G: 0.488,
                "0": 0.061,
                "1": 0.122,
                "2": 0.244,
                "3": 0.488,
            }
            # Accept both enum and string
            if isinstance(scale, SensorConfig.Accel.Scale):
                factor = scale_map[scale]
            elif isinstance(scale, str):
                factor = scale_map[scale]
            else:
                raise ValueError(f"Unknown scale: {scale}")
            return (float(lsb) * factor * 9.80665) / 1000

    class Gyro:
        """
        Gyroscope configuration.
        """

        class Scale(StrEnum):
            DPS_125 = "0"
            DPS_250 = "1"
            DPS_500 = "2"
            DPS_1000 = "3"
            DPS_2000 = "4"

            @classmethod
            def to_dps(cls, value):
                """
                Convert a Scale enum value or string to its corresponding DPS setting.

                Examples:
                    Gyro.Scale.to_dps(Gyro.Scale.DPS_250)      # returns 250
                    Gyro.Scale.to_dps("2")                     # returns 500
                    Gyro.Scale.to_dps(Gyro.Scale.DPS_2000)     # returns 2000
                """
                _scale_dps_map = {
                    "0": 125,
                    "1": 250,
                    "2": 500,
                    "3": 1000,
                    "4": 2000,
                }

                if isinstance(value, cls):
                    key = value.value
                elif isinstance(value, str):
                    key = value
                else:
                    raise ValueError(f"Cannot convert {value!r} to DPS for Gyro.Scale")
                return _scale_dps_map[key]

        class SamplingRate(StrEnum):
            RATE_12HZ = "0"
            RATE_25HZ = "1"
            RATE_50HZ = "2"
            RATE_100HZ = "3"

            @classmethod
            def to_hz(cls, value):
                """
                Convert a SamplingRate enum value or string to its corresponding Hz setting.

                Examples:
                    Gyro.SamplingRate.to_hz(Gyro.SamplingRate.RATE_25HZ)   # returns 25
                    Gyro.SamplingRate.to_hz("3")                            # returns 100
                    Gyro.SamplingRate.to_hz(Gyro.SamplingRate.RATE_12HZ) # returns 12
                """
                _rate_hz_map = {
                    "0": 12,
                    "1": 25,
                    "2": 50,
                    "3": 100,
                }

                if isinstance(value, cls):
                    key = value.value
                elif isinstance(value, str):
                    key = value
                else:
                    raise ValueError(
                        f"Cannot convert {value!r} to Hz for Gyro.SamplingRate"
                    )
                return _rate_hz_map[key]

        @staticmethod
        def lsb_to_dps(lsb: int, scale: "SensorConfig.Gyro.Scale") -> float:
            """
            Convert raw sensor integer value (lsb) to degrees per second (dps) based on the scale.

            Args:
                lsb (int): Raw sensor value (int16_t from device)
                scale (Gyro.Scale or str): Measurement scale (125, 250, 500, 1000, 2000 DPS)

            Returns:
                float: Value in milli-degrees per second (mdps)

            Conversion factors:
                125 DPS  -> 4.375 mdps/LSB
                250 DPS  -> 8.750 mdps/LSB
                500 DPS  -> 17.50 mdps/LSB
                1000 DPS -> 35.0 mdps/LSB
                2000 DPS -> 70.0 mdps/LSB
            """
            scale_map = {
                SensorConfig.Gyro.Scale.DPS_125: 4.375,
                SensorConfig.Gyro.Scale.DPS_250: 8.750,
                SensorConfig.Gyro.Scale.DPS_500: 17.50,
                SensorConfig.Gyro.Scale.DPS_1000: 35.0,
                SensorConfig.Gyro.Scale.DPS_2000: 70.0,
                "0": 4.375,
                "1": 8.750,
                "2": 17.50,
                "3": 35.0,
                "4": 70.0,
            }
            # Accept both enum and string
            if isinstance(scale, SensorConfig.Gyro.Scale):
                factor = scale_map[scale]
            elif isinstance(scale, str):
                factor = scale_map[scale]
            else:
                raise ValueError(f"Unknown scale: {scale}")
            return float(lsb) * factor / 1000

    class Mag:
        """
        Magnetometer configuration.
        """

        class SamplingRate(StrEnum):
            RATE_10HZ = "0"
            RATE_20HZ = "1"
            RATE_50HZ = "2"
            RATE_100HZ = "3"

            @classmethod
            def to_hz(cls, value):
                """
                Convert a SamplingRate enum value or string to its corresponding Hz setting.

                Examples:
                    Mag.SamplingRate.to_hz(Mag.SamplingRate.RATE_20HZ)   # returns 20
                    Mag.SamplingRate.to_hz("2")                          # returns 50
                    Mag.SamplingRate.to_hz(Mag.SamplingRate.RATE_10HZ) # returns 10
                """
                _rate_hz_map = {
                    "0": 10,
                    "1": 20,
                    "2": 50,
                    "3": 100,
                }

                if isinstance(value, cls):
                    key = value.value
                elif isinstance(value, str):
                    key = value
                else:
                    raise ValueError(
                        f"Cannot convert {value!r} to Hz for Mag.SamplingRate"
                    )
                return _rate_hz_map[key]

        @staticmethod
        def lsb_to_gauss(lsb: int) -> float:
            """
            Convert raw sensor integer value (lsb) to Gauss (Gauss).

            Args:
                lsb (int): Raw sensor value (int16_t from device)

            Returns:
                float: Value in milli-Gauss (mGauss)

            Conversion factor:
                1.5 mGauss/LSB
            """
            return float(lsb) * 1.5 / 1000

    class Temp:
        """
        Temperature sensor configuration.
        """

        class SamplingRate(StrEnum):
            RATE_0_5HZ = "0.5"
            RATE_1HZ = "1"
            RATE_2HZ = "2"
            RATE_4HZ = "4"
            RATE_8HZ = "8"
            RATE_16HZ = "16"
            RATE_32HZ = "32"
            RATE_64HZ = "64"

    class PPG:
        """
        PPG configuration.
        """

        class SamplingRate(StrEnum):
            RATE_25HZ = "25"
            RATE_50HZ = "50"
            RATE_100HZ = "100"

        class LEDCurrent(StrEnum):
            CURRENT_31MA = "31"
            CURRENT_62MA = "62"
            CURRENT_93MA = "93"
            CURRENT_124MA = "124"

        class Wavelength(IntEnum):
            LED_RED = 1
            LED_GREEN = 2
            LED_INFRARED = 4

        class Wavelength(IntEnum):
            LED_RED = 1
            LED_GREEN = 2
            LED_INFRARED = 4

    class HR:
        """
        Heart Rate sensor config.
        """

        Period = Periodicity

    class SpO2:
        """
        SpO2 config.
        """

        Period = Periodicity

    class HRV:
        """
        HRV config. (uses HR internally)
        """

        pass

    class Respiration:
        """
        Respiration Rate config. (no period)
        """

        pass

    class BP:
        """
        Blood Pressure Metrics config.
        """

        class Period(StrEnum):
            EVERY_12S = "0"
            EVERY_30S = "1"
            EVERY_MINUTE = "2"
