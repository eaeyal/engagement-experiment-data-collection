""" 
This file is licensed under the MIT License.
See the LICENSE file in the root directory for full license text.

Copyright (c) 2025 OmniBuds Ltd

Author: Yang Liu  
Email: yang.liu3e@gmail.com  

"""

__all__ = [
    # Base & Core
    "BaseSensorCommand",
    "OmniBudsCommand",
    "OmniBudsComManager",
    "OmniBudsParsedPacket",
    "OmniBudsUUID",
    "SensorConfig",
    "OmniBudsUtils",
    # Identifiers
    "PeripheralID",
    "MsgID",
    "MsgType",
    # Sensor Commands
    "AccelerometerCommand",
    "GyroCommand",
    "MagnetometerCommand",
    "PPGRawCommand",
    "TempObjectCommand",
    "HeartRateCommand",
    "HRVCommand",
    "SpO2Command",
    "RespirationRateCommand",
    # System Commands
    "TimestepUpdateCommand",
    "PowerManagementCommand",
    "FirmwareVersionCommand",
    "EarbudsSleepCommand",
    # Event Commands
    "ButtonPressDetectionCommand",
    "InEarDectetionCommand",
]


# ============================
# Metadata
# ============================

__copyright__ = "OmniBuds Ltd 2025"
__license__ = "Mozilla Public License Version 2.0"
__summary__ = "A Python library for Bluetooth LE communication with OmniBuds"
__uri__ = "https://github.com/OmniBudsAI/OmniBuds-PyPI"

# ============================
# Imports
# ============================

import platform
import logging
import asyncio

from ._version import __version__

# Base & Core components
from omnibuds.omnibuds import (
    OmniBudsCommand,
    OmniBudsComManager,
    OmniBudsParsedPacket,
    OmniBudsUtils,
)
from omnibuds.base import BaseSensorCommand

# Enumerations and UUIDs
from omnibuds.ids import (
    PeripheralID,
    MsgID,
    MsgType,
    OmniBudsUUID,
    SensorConfig,
)

# Sensor command classes (auto-import all)
from omnibuds.com import *


# Global configuration
from omnibuds.conf import GlobalConfig


# ============================
# Asyncio Compatibility for Linux
# ============================

if platform.system() == "Linux":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


# ============================
# Logger Configuration
# ============================

logger = logging.getLogger("omnibuds")
logger.setLevel(logging.DEBUG if GlobalConfig.DEBUG else logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
