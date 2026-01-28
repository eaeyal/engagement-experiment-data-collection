import asyncio
import logging
from bleak import BleakClient, BleakScanner
from pylsl import StreamInfo, StreamOutlet

# Import core OmniBuds components
from omnibuds import OmniBudsComManager, OmniBudsCommand, OmniBudsParsedPacket, OmniBudsUUID
from omnibuds.ids import PeripheralID, SensorConfig as SC, Periodicity

# Import sensor commands
from omnibuds.com import (
    PPGRawCommand,
    AccelerometerCommand,
    GyroCommand,
    MagnetometerCommand,
    HeartRateCommand,
    HRVCommand,
    SpO2Command,
    RespirationRateCommand
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEVICE_NAME = "OmniBuds-4167"
CHAR_UUID = OmniBudsUUID.CHAR_UUID_RIGHT
SAMPLE_RATE = 100  # Nominal sample rate for high-freq sensors

# Stream Names
STREAM_NAME_PPG = 'OmniBuds_PPG'
STREAM_TYPE_PPG = 'PPG'
STREAM_NAME_ACC = 'OmniBuds_Accel'
STREAM_NAME_GYRO = 'OmniBuds_Gyro'
STREAM_NAME_MAG = 'OmniBuds_Mag'
# New Stream Names
STREAM_NAME_HR = 'OmniBuds_HR'
STREAM_NAME_HRV = 'OmniBuds_HRV'
STREAM_NAME_SPO2 = 'OmniBuds_SpO2'
STREAM_NAME_RESP = 'OmniBuds_Resp'

async def main():
    # Step 1: Scan for the OmniBuds device
    logger.info(f"Scanning for device: {DEVICE_NAME}")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME)
    if device is None:
        logger.error(f"Device {DEVICE_NAME} not found.")
        return

    logger.info(f"Found device: {device.name} at {device.address}")

    # Step 2: Connect
    async with BleakClient(device, timeout=20.0, winrt={"use_cached_services": False}) as client:
        logger.info("Connected to device.")

        # Force pairing (Windows specific fix)
        try:
            logger.info("Requesting pairing (Protection Level 2)...")
            await client.pair(protection_level=2)
            logger.info("Pairing command accepted.")
        except Exception as e:
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

        # --- Motion Streams ---
        # Accelerometer
        info_acc = StreamInfo(STREAM_NAME_ACC, 'Accelerometer', 3, SAMPLE_RATE, 'float32', 'omnibuds_acc')
        info_acc.desc().append_child_value("manufacturer", "OmniBuds")
        channels_acc = info_acc.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_acc.append_child("channel").append_child_value("label", f"Accel_{axis}").append_child_value("unit", "g")
        outlet_acc = StreamOutlet(info_acc)

        # Gyroscope
        info_gyro = StreamInfo(STREAM_NAME_GYRO, 'Gyroscope', 3, SAMPLE_RATE, 'float32', 'omnibuds_gyro')
        info_gyro.desc().append_child_value("manufacturer", "OmniBuds")
        channels_gyro = info_gyro.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_gyro.append_child("channel").append_child_value("label", f"Gyro_{axis}").append_child_value("unit", "dps")
        outlet_gyro = StreamOutlet(info_gyro)

        # Magnetometer
        info_mag = StreamInfo(STREAM_NAME_MAG, 'Magnetometer', 3, SAMPLE_RATE, 'float32', 'omnibuds_mag')
        info_mag.desc().append_child_value("manufacturer", "OmniBuds")
        channels_mag = info_mag.desc().append_child("channels")
        for axis in ["X", "Y", "Z"]:
            channels_mag.append_child("channel").append_child_value("label", f"Mag_{axis}").append_child_value("unit", "Gauss")
        outlet_mag = StreamOutlet(info_mag)

        # --- Bio-metrics Streams (Irregular Sampling) ---
        # Heart Rate
        info_hr = StreamInfo(STREAM_NAME_HR, 'HeartRate', 1, 0, 'float32', 'omnibuds_hr')
        info_hr.desc().append_child_value("manufacturer", "OmniBuds")
        info_hr.desc().append_child("channels").append_child("channel").append_child_value("label", "HR").append_child_value("unit", "bpm")
        outlet_hr = StreamOutlet(info_hr)

        # HRV
        info_hrv = StreamInfo(STREAM_NAME_HRV, 'HRV', 1, 0, 'float32', 'omnibuds_hrv')
        info_hrv.desc().append_child_value("manufacturer", "OmniBuds")
        info_hrv.desc().append_child("channels").append_child("channel").append_child_value("label", "HRV").append_child_value("unit", "ms")
        outlet_hrv = StreamOutlet(info_hrv)

        # SpO2
        info_spo2 = StreamInfo(STREAM_NAME_SPO2, 'SpO2', 1, 0, 'float32', 'omnibuds_spo2')
        info_spo2.desc().append_child_value("manufacturer", "OmniBuds")
        info_spo2.desc().append_child("channels").append_child("channel").append_child_value("label", "SpO2").append_child_value("unit", "percent")
        outlet_spo2 = StreamOutlet(info_spo2)

        # Respiration Rate
        info_resp = StreamInfo(STREAM_NAME_RESP, 'Respiration', 1, 0, 'float32', 'omnibuds_resp')
        info_resp.desc().append_child_value("manufacturer", "OmniBuds")
        info_resp.desc().append_child("channels").append_child("channel").append_child_value("label", "RespRate").append_child_value("unit", "rpm")
        outlet_resp = StreamOutlet(info_resp)

        logger.info("All LSL streams created and ready.")

        # =========================================================
        # Data Handler
        # =========================================================
        def data_handler(sender, data):
            try:
                parsed = OmniBudsParsedPacket(data)

                # --- High Frequency Sensors ---
                if parsed.peripheral_id == PeripheralID.PPG_RAW:
                    for ts, green, red, ir in parsed.get_samples():
                        outlet_ppg.push_sample([int(green), int(red), int(ir)])
                
                elif parsed.peripheral_id == PeripheralID.ACC:
                    for ts, x, y, z in parsed.get_samples():
                        outlet_acc.push_sample([float(x), float(y), float(z)])
                
                elif parsed.peripheral_id == PeripheralID.GYRO:
                    for ts, x, y, z in parsed.get_samples():
                        outlet_gyro.push_sample([float(x), float(y), float(z)])

                elif parsed.peripheral_id == PeripheralID.MAG:
                    for ts, x, y, z in parsed.get_samples():
                        outlet_mag.push_sample([float(x), float(y), float(z)])

                # --- Bio-metrics Sensors ---
                elif parsed.peripheral_id == PeripheralID.HR:
                    for ts, val in parsed.get_samples():
                        outlet_hr.push_sample([float(val)])

                elif parsed.peripheral_id == PeripheralID.HRV:
                    for ts, val in parsed.get_samples():
                        outlet_hrv.push_sample([float(val)])

                elif parsed.peripheral_id == PeripheralID.SPO2:
                    for ts, val in parsed.get_samples():
                        outlet_spo2.push_sample([float(val)])
                
                elif parsed.peripheral_id == PeripheralID.RESP_RATE:
                    for ts, val in parsed.get_samples():
                        outlet_resp.push_sample([float(val)])

            except Exception as e:
                logger.debug(f"Error parsing/pushing data: {e}")

        # Build and start notifications
        handler = manager.build_omnibuds_handler(user_handler=data_handler)
        
        logger.info("Enabling notifications...")
        await client.start_notify(CHAR_UUID, handler)
        logger.info("Notifications enabled.")
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

        # --- Motion Config ---
        acc_cmd = AccelerometerCommand(client, manager)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["sampling_rate"], data=SC.Accel.SamplingRate.RATE_100HZ)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["scale_range"], data=SC.Accel.Scale.SCALE_4G)
        await acc_cmd.send_command(CHAR_UUID, endpoint=acc_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)

        gyro_cmd = GyroCommand(client, manager)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["sampling_rate"], data=SC.Gyro.SamplingRate.RATE_100HZ)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["scale_range"], data=SC.Gyro.Scale.DPS_1000)
        await gyro_cmd.send_command(CHAR_UUID, endpoint=gyro_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)

        mag_cmd = MagnetometerCommand(client, manager)
        await mag_cmd.send_command(CHAR_UUID, endpoint=mag_cmd.CONFIG["sampling_rate"], data=SC.Mag.SamplingRate.RATE_100HZ)
        await mag_cmd.send_command(CHAR_UUID, endpoint=mag_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        logger.info("Motion sensors enabled.")

        # --- Bio-metrics Config ---
        # Heart Rate
        hr_cmd = HeartRateCommand(client, manager)
        await hr_cmd.send_command(CHAR_UUID, endpoint=hr_cmd.CONFIG["periodicity"], data=Periodicity.EVERY_SECOND)
        await hr_cmd.send_command(CHAR_UUID, endpoint=hr_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        
        # HRV
        hrv_cmd = HRVCommand(client, manager)
        await hrv_cmd.send_command(CHAR_UUID, endpoint=hrv_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)

        # SpO2
        spo2_cmd = SpO2Command(client, manager)
        await spo2_cmd.send_command(CHAR_UUID, endpoint=spo2_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)

        # Respiration Rate
        resp_cmd = RespirationRateCommand(client, manager)
        await resp_cmd.send_command(CHAR_UUID, endpoint=resp_cmd.CONFIG["enable"], data=SC.SensorToggle.ENABLE)
        
        logger.info("Bio-metrics sensors enabled (HR, HRV, SpO2, Resp).")

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
            
            # --- Motion Cleanup ---
            await acc_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=acc_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await gyro_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=gyro_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await mag_cmd.send_command(CHAR_UUID=CHAR_UUID, endpoint=mag_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)

            # --- Bio-metrics Cleanup ---
            await hr_cmd.send_command(CHAR_UUID, endpoint=hr_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await hrv_cmd.send_command(CHAR_UUID, endpoint=hrv_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await spo2_cmd.send_command(CHAR_UUID, endpoint=spo2_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            await resp_cmd.send_command(CHAR_UUID, endpoint=resp_cmd.CONFIG["enable"], data=SC.SensorToggle.DISABLE)
            
            logger.info("Sensors disabled.")
            await client.stop_notify(CHAR_UUID)
            logger.info("Notifications stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass