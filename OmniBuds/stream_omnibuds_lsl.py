import asyncio
import logging
from bleak import BleakClient, BleakScanner
from pylsl import StreamInfo, StreamOutlet

# Import core OmniBuds components
from omnibuds import OmniBudsComManager, OmniBudsCommand, OmniBudsParsedPacket, OmniBudsUUID
from omnibuds.ids import PeripheralID, SensorConfig as SC

# Import sensor commands
# Note: PPGRawCommand is preserved. Accelerometer, Gyro, and Magnetometer added.
from omnibuds.com import (
    PPGRawCommand,
    AccelerometerCommand,
    GyroCommand,
    MagnetometerCommand
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEVICE_NAME = "OmniBuds-4167"
CHAR_UUID = OmniBudsUUID.CHAR_UUID_RIGHT
SAMPLE_RATE = 100  # Nominal sample rate in Hz

# Stream Names
STREAM_NAME_PPG = 'OmniBuds_PPG'
STREAM_TYPE_PPG = 'PPG'
# New Stream Names
STREAM_NAME_ACC = 'OmniBuds_Accel'
STREAM_NAME_GYRO = 'OmniBuds_Gyro'
STREAM_NAME_MAG = 'OmniBuds_Mag'

async def main():
    # Step 1: Scan for the OmniBuds device
    logger.info(f"Scanning for device: {DEVICE_NAME}")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME)
    if device is None:
        logger.error(f"Device {DEVICE_NAME} not found.")
        return

    logger.info(f"Found device: {device.name} at {device.address}")

    # Step 2: Connect
    async with BleakClient(device, winrt={"use_cached_services": False}) as client:
        logger.info("Connected to device.")

        # Initialize OmniBuds communication
        manager = OmniBudsComManager(client)
        OmniBudsCommand.init(client, manager)

        # =========================================================
        # LSL Stream Setup
        # =========================================================

        # --- PPG Stream (PRESERVED EXACTLY) ---
        info_ppg = StreamInfo(STREAM_NAME_PPG, STREAM_TYPE_PPG, 3, SAMPLE_RATE, 'int32', 'omnibuds_ppg')
        info_ppg.desc().append_child_value("manufacturer", "OmniBuds")
        channels_ppg = info_ppg.desc().append_child("channels")
        channels_ppg.append_child("channel").append_child_value("label", "Green").append_child_value("unit", "raw").append_child_value("type", "PPG")
        channels_ppg.append_child("channel").append_child_value("label", "Red").append_child_value("unit", "raw").append_child_value("type", "PPG")
        channels_ppg.append_child("channel").append_child_value("label", "IR").append_child_value("unit", "raw").append_child_value("type", "PPG")
        outlet_ppg = StreamOutlet(info_ppg)
        logger.info(f"LSL stream '{STREAM_NAME_PPG}' created and ready.")

        # --- Accelerometer Stream (NEW) ---
        info_acc = StreamInfo(STREAM_NAME_ACC, 'Accelerometer', 3, SAMPLE_RATE, 'float32', 'omnibuds_acc')
        info_acc.desc().append_child_value("manufacturer", "OmniBuds")
        channels_acc = info_acc.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_acc.append_child("channel").append_child_value("label", f"Accel_{axis}").append_child_value("unit", "g")
        outlet_acc = StreamOutlet(info_acc)
        logger.info(f"LSL stream '{STREAM_NAME_ACC}' created and ready.")

        # --- Gyroscope Stream (NEW) ---
        info_gyro = StreamInfo(STREAM_NAME_GYRO, 'Gyroscope', 3, SAMPLE_RATE, 'float32', 'omnibuds_gyro')
        info_gyro.desc().append_child_value("manufacturer", "OmniBuds")
        channels_gyro = info_gyro.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_gyro.append_child("channel").append_child_value("label", f"Gyro_{axis}").append_child_value("unit", "dps")
        outlet_gyro = StreamOutlet(info_gyro)
        logger.info(f"LSL stream '{STREAM_NAME_GYRO}' created and ready.")

        # --- Magnetometer Stream (NEW) ---
        info_mag = StreamInfo(STREAM_NAME_MAG, 'Magnetometer', 3, SAMPLE_RATE, 'float32', 'omnibuds_mag')
        info_mag.desc().append_child_value("manufacturer", "OmniBuds")
        channels_mag = info_mag.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_mag.append_child("channel").append_child_value("label", f"Mag_{axis}").append_child_value("unit", "Gauss")
        outlet_mag = StreamOutlet(info_mag)
        logger.info(f"LSL stream '{STREAM_NAME_MAG}' created and ready.")


        # =========================================================
        # Data Handler
        # =========================================================
        def data_handler(sender, data):
            try:
                parsed = OmniBudsParsedPacket(data)

                # --- PPG Handling (PRESERVED EXACTLY) ---
                if parsed.peripheral_id == PeripheralID.PPG_RAW:
                    samples = parsed.get_samples()
                    for ts, green, red, ir in samples:
                        sample = [int(green), int(red), int(ir)]
                        lsl_ts = ts / 1000.0
                        outlet_ppg.push_sample(sample)
                        # print(f"Pushed PPG sample to LSL - TS: {ts}, Green: {green}, Red: {red}, IR: {ir}")
                
                # --- Accelerometer Handling (NEW) ---
                elif parsed.peripheral_id == PeripheralID.ACC:
                    samples = parsed.get_samples() # returns (ts, x_str, y_str, z_str)
                    for ts, x, y, z in samples:
                        # Values come as strings from parsed packet, convert to float
                        sample = [float(x), float(y), float(z)]
                        lsl_ts = ts / 1000.0
                        outlet_acc.push_sample(sample)
                
                # --- Gyroscope Handling (NEW) ---
                elif parsed.peripheral_id == PeripheralID.GYRO:
                    samples = parsed.get_samples()
                    for ts, x, y, z in samples:
                        sample = [float(x), float(y), float(z)]
                        lsl_ts = ts / 1000.0
                        outlet_gyro.push_sample(sample)

                # --- Magnetometer Handling (NEW) ---
                elif parsed.peripheral_id == PeripheralID.MAG:
                    samples = parsed.get_samples()
                    for ts, x, y, z in samples:
                        sample = [float(x), float(y), float(z)]
                        lsl_ts = ts / 1000.0
                        outlet_mag.push_sample(sample)

            except Exception as e:
                logger.debug(f"Error parsing/pushing data: {e}")

        # Build and start notifications
        handler = manager.build_omnibuds_handler(user_handler=data_handler)
        await client.start_notify(CHAR_UUID, handler)
        logger.info("Notifications enabled.")

        # Wait briefly for any initial messages
        await asyncio.sleep(1)

        # =========================================================
        # Sensor Configuration
        # =========================================================

        # --- PPG Config (PRESERVED EXACTLY) ---
        ppg_cmd = PPGRawCommand(client, manager)
        await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["sampling_rate"], data=SC.PPG.SamplingRate.RATE_100HZ)
        logger.info("PPG sampling rate set to 100Hz.")
        await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["led_current"], data=SC.PPG.LEDCurrent.CURRENT_31MA)
        logger.info("PPG LED current set to 31mA.")
        await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["enable"], data="7")
        logger.info("PPG sensor enabled with all channels (bitmask 7).")

        # --- Accelerometer Config (NEW) ---
        acc_cmd = AccelerometerCommand(client, manager)
        # Rate: 100Hz ("3"), Scale: 4G ("1")
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["sampling_rate"], data=SC.Accel.SamplingRate.RATE_100HZ)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["scale_range"], data=SC.Accel.Scale.SCALE_4G)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Accelerometer enabled (100Hz, 4G).")

        # --- Gyroscope Config (NEW) ---
        gyro_cmd = GyroCommand(client, manager)
        # Rate: 100Hz ("3"), Scale: 1000dps ("3")
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["sampling_rate"], data=SC.Gyro.SamplingRate.RATE_100HZ)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["scale_range"], data=SC.Gyro.Scale.DPS_1000)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Gyroscope enabled (100Hz, 1000dps).")

        # --- Magnetometer Config (NEW) ---
        mag_cmd = MagnetometerCommand(client, manager)
        # Rate: 100Hz ("3")
        await mag_cmd.send_command(CHAR_UUID, endpoint=mag_cmd.CONFIG["sampling_rate"], data=SC.Mag.SamplingRate.RATE_100HZ)
        await mag_cmd.send_command(CHAR_UUID, endpoint=mag_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Magnetometer enabled (100Hz).")

        # Keep the script running
        try:
            logger.info("Streaming all sensors to LSL... Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Stopping...")

            # --- PPG Cleanup (PRESERVED EXACTLY) ---
            await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["enable"], data="0")
            logger.info("PPG sensor disabled.")

            # --- New Sensors Cleanup ---
            await acc_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=acc_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await gyro_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=gyro_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await mag_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=mag_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            logger.info("IMU sensors disabled.")

            await client.stop_notify(CHAR_UUID)
            logger.info("Notifications stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass