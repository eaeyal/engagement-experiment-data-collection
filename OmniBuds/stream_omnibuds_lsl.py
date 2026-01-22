import asyncio
import logging
from bleak import BleakClient, BleakScanner
from omnibuds import OmniBudsComManager, OmniBudsCommand, OmniBudsParsedPacket, OmniBudsUUID
from omnibuds.com import PPGRawCommand
from omnibuds.ids import PeripheralID, SensorConfig as SC
from pylsl import StreamInfo, StreamOutlet, local_clock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEVICE_NAME = "OmniBuds-4167"
CHAR_UUID = OmniBudsUUID.CHAR_UUID_RIGHT  # Assuming right earbud; change to LEFT if needed
STREAM_NAME = 'OmniBuds_PPG'
STREAM_TYPE = 'PPG'
SAMPLE_RATE = 100  # Nominal sample rate in Hz

async def main():
    # Step 1: Scan for the OmniBuds device
    logger.info(f"Scanning for device: {DEVICE_NAME}")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME)
    if device is None:
        logger.error(f"Device {DEVICE_NAME} not found.")
        return

    logger.info(f"Found device: {device.name} at {device.address}")

    # Step 2: Connect (pair manually via Windows Bluetooth settings first)
    async with BleakClient(device, winrt={"use_cached_services": False}) as client:
        logger.info("Connected to device.")

        # Initialize OmniBuds communication
        manager = OmniBudsComManager(client)
        OmniBudsCommand.init(client, manager)

        # Create LSL stream info and outlet
        info = StreamInfo(STREAM_NAME, STREAM_TYPE, 3, SAMPLE_RATE, 'int32', 'omnibuds_ppg')
        info.desc().append_child_value("manufacturer", "OmniBuds")
        channels = info.desc().append_child("channels")
        channels.append_child("channel") \
            .append_child_value("label", "Green") \
            .append_child_value("unit", "raw") \
            .append_child_value("type", "PPG")
        channels.append_child("channel") \
            .append_child_value("label", "Red") \
            .append_child_value("unit", "raw") \
            .append_child_value("type", "PPG")
        channels.append_child("channel") \
            .append_child_value("label", "IR") \
            .append_child_value("unit", "raw") \
            .append_child_value("type", "PPG")
        outlet = StreamOutlet(info)
        logger.info(f"LSL stream '{STREAM_NAME}' created and ready.")

        # Custom handler to process PPG data and push to LSL
        def ppg_handler(sender, data):
            try:
                parsed = OmniBudsParsedPacket(data)
                if parsed.peripheral_id == PeripheralID.PPG_RAW:
                    samples = parsed.get_samples()
                    for ts, green, red, ir in samples:
                        # Convert values to int (assuming they are strings)
                        sample = [int(green), int(red), int(ir)]
                        # Convert device timestamp (ms) to seconds for LSL
                        lsl_ts = ts / 1000.0
                        outlet.push_sample(sample, lsl_ts)
                        print(f"Pushed PPG sample to LSL - TS: {ts}, Green: {green}, Red: {red}, IR: {ir}")
            except Exception as e:
                logger.debug(f"Error parsing/pushing data: {e}")

        # Build and start notifications
        handler = manager.build_omnibuds_handler(user_handler=ppg_handler)
        await client.start_notify(CHAR_UUID, handler)
        logger.info("Notifications enabled.")

        # Wait briefly for any initial messages
        await asyncio.sleep(1)

        # Step 3: Configure and enable PPG sensor
        ppg_cmd = PPGRawCommand(client, manager)
        
        # Set sampling rate to 100Hz
        await ppg_cmd.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=ppg_cmd.CONFIG["sampling_rate"],
            data=SC.PPG.SamplingRate.RATE_100HZ
        )
        logger.info("PPG sampling rate set to 100Hz.")
        
        # Set LED current to 31mA (to avoid saturation)
        await ppg_cmd.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=ppg_cmd.CONFIG["led_current"],
            data=SC.PPG.LEDCurrent.CURRENT_31MA
        )
        logger.info("PPG LED current set to 31mA.")
        
        # Enable PPG with all channels (bitmask 7)
        await ppg_cmd.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=ppg_cmd.CONFIG["enable"],
            data="7"  # red (1) + green (2) + IR (4)
        )
        logger.info("PPG sensor enabled with all channels (bitmask 7). Streaming data to LSL...")

        # Keep the script running to receive and stream data (press Ctrl+C to stop)
        try:
            await asyncio.sleep(3600)  # Run for 1 hour or adjust as needed
        except asyncio.CancelledError:
            pass

        # Cleanup: Disable PPG before disconnecting
        await ppg_cmd.send_command(
            CHAR_UUID=CHAR_UUID,
            endpoint=ppg_cmd.CONFIG["enable"],
            data="0"
        )
        logger.info("PPG sensor disabled.")
        await client.stop_notify(CHAR_UUID)
        logger.info("Notifications stopped.")

if __name__ == "__main__":
    asyncio.run(main())