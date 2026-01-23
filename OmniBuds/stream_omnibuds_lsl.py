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
    # Increased timeout to 20s to allow Windows time to handle the pairing popup
    async with BleakClient(device, timeout=20.0, winrt={"use_cached_services": False}) as client:
        logger.info("Connected to device.")

        # =========================================================
        # FORCE PAIRING REQUEST (The Fix)
        # =========================================================
        try:
            logger.info("Requesting pairing (Protection Level 2)...")
            # This triggers the Windows "Add a device" popup if not already paired
            await client.pair(protection_level=2)
            logger.info("Pairing command accepted.")
        except Exception as e:
            # If this fails, it usually means we are already paired or the 
            # library version is weird. We log it and keep going.
            logger.warning(f"Pairing skipped or warning received: {e}")

        # Initialize OmniBuds communication
        manager = OmniBudsComManager(client)
        OmniBudsCommand.init(client, manager)

        # =========================================================
        # LSL Stream Setup
        # =========================================================

        # --- PPG Stream ---
        info_ppg = StreamInfo(STREAM_NAME_PPG, STREAM_TYPE_PPG, 3, SAMPLE_RATE, 'int32', 'omnibuds_ppg')
        info_ppg.desc().append_child_value("manufacturer", "OmniBuds")
        channels_ppg = info_ppg.desc().append_child("channels")
        channels_ppg.append_child("channel").append_child_value("label", "Green").append_child_value("unit", "raw").append_child_value("type", "PPG")
        channels_ppg.append_child("channel").append_child_value("label", "Red").append_child_value("unit", "raw").append_child_value("type", "PPG")
        channels_ppg.append_child("channel").append_child_value("label", "IR").append_child_value("unit", "raw").append_child_value("type", "PPG")
        outlet_ppg = StreamOutlet(info_ppg)
        logger.info(f"LSL stream '{STREAM_NAME_PPG}' created and ready.")

        # --- Accelerometer Stream ---
        info_acc = StreamInfo(STREAM_NAME_ACC, 'Accelerometer', 3, SAMPLE_RATE, 'float32', 'omnibuds_acc')
        info_acc.desc().append_child_value("manufacturer", "OmniBuds")
        channels_acc = info_acc.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_acc.append_child("channel").append_child_value("label", f"Accel_{axis}").append_child_value("unit", "g")
        outlet_acc = StreamOutlet(info_acc)
        logger.info(f"LSL stream '{STREAM_NAME_ACC}' created and ready.")

        # --- Gyroscope Stream ---
        info_gyro = StreamInfo(STREAM_NAME_GYRO, 'Gyroscope', 3, SAMPLE_RATE, 'float32', 'omnibuds_gyro')
        info_gyro.desc().append_child_value("manufacturer", "OmniBuds")
        channels_gyro = info_gyro.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_gyro.append_child("channel").append_child_value("label", f"Gyro_{axis}").append_child_value("unit", "dps")
        outlet_gyro = StreamOutlet(info_gyro)
        logger.info(f"LSL stream '{STREAM_NAME_GYRO}' created and ready.")

        # --- Magnetometer Stream ---
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

                # --- PPG Handling ---
                if parsed.peripheral_id == PeripheralID.PPG_RAW:
                    samples = parsed.get_samples()
                    for ts, green, red, ir in samples:
                        sample = [int(green), int(red), int(ir)]
                        outlet_ppg.push_sample(sample)
                
                # --- Accelerometer Handling ---
                elif parsed.peripheral_id == PeripheralID.ACC:
                    samples = parsed.get_samples() 
                    for ts, x, y, z in samples:
                        sample = [float(x), float(y), float(z)]
                        outlet_acc.push_sample(sample)
                
                # --- Gyroscope Handling ---
                elif parsed.peripheral_id == PeripheralID.GYRO:
                    samples = parsed.get_samples()
                    for ts, x, y, z in samples:
                        sample = [float(x), float(y), float(z)]
                        outlet_gyro.push_sample(sample)

                # --- Magnetometer Handling ---
                elif parsed.peripheral_id == PeripheralID.MAG:
                    samples = parsed.get_samples()
                    for ts, x, y, z in samples:
                        sample = [float(x), float(y), float(z)]
                        outlet_mag.push_sample(sample)

            except Exception as e:
                logger.debug(f"Error parsing/pushing data: {e}")

        # Build and start notifications
        handler = manager.build_omnibuds_handler(user_handler=data_handler)
        
        logger.info("Enabling notifications...")
        # If pairing worked above, this line will now succeed
        await client.start_notify(CHAR_UUID, handler)
        logger.info("Notifications enabled.")

        # Wait briefly for any initial messages
        await asyncio.sleep(1)

        # =========================================================
        # Sensor Configuration
        # =========================================================

        # --- PPG Config ---
        ppg_cmd = PPGRawCommand(client, manager)
        await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["sampling_rate"], data=SC.PPG.SamplingRate.RATE_100HZ)
        await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["led_current"], data=SC.PPG.LEDCurrent.CURRENT_31MA)
        await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["enable"], data="7")
        logger.info("PPG sensor enabled.")

        # --- Accelerometer Config ---
        acc_cmd = AccelerometerCommand(client, manager)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["sampling_rate"], data=SC.Accel.SamplingRate.RATE_100HZ)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["scale_range"], data=SC.Accel.Scale.SCALE_4G)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Accelerometer enabled.")

        # --- Gyroscope Config ---
        gyro_cmd = GyroCommand(client, manager)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["sampling_rate"], data=SC.Gyro.SamplingRate.RATE_100HZ)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["scale_range"], data=SC.Gyro.Scale.DPS_1000)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Gyroscope enabled.")

        # --- Magnetometer Config ---
        mag_cmd = MagnetometerCommand(client, manager)
        await mag_cmd.send_command(CHAR_UUID, endpoint=mag_cmd.CONFIG["sampling_rate"], data=SC.Mag.SamplingRate.RATE_100HZ)
        await mag_cmd.send_command(CHAR_UUID, endpoint=mag_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Magnetometer enabled.")

        # Keep the script running
        try:
            logger.info("Streaming all sensors to LSL... Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Stopping...")

            # --- PPG Cleanup ---
            await ppg_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=ppg_cmd.CONFIG["enable"], data="0")
            
            # --- New Sensors Cleanup ---
            await acc_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=acc_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await gyro_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=gyro_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await mag_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=mag_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            
            logger.info("Sensors disabled.")
            await client.stop_notify(CHAR_UUID)
            logger.info("Notifications stopped.")
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass