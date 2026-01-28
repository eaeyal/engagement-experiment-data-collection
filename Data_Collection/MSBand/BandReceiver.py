import socket
import struct
from pylsl import StreamInfo, StreamOutlet

def start_band_receiver():
    # Set up LSL streams
    # GSR stream: 1 channel (resistance in kOhms)
    gsr_info = StreamInfo('MSBand_GSR', 'GSR', 1, 0, 'float32', 'msband_gsr')
    gsr_outlet = StreamOutlet(gsr_info)

    # HR stream: 2 channels (heart rate in bpm, quality flag: 1 for Locked, 0 otherwise)
    hr_info = StreamInfo('MSBand_HR', 'HR', 2, 0, 'float32', 'msband_hr')
    hr_outlet = StreamOutlet(hr_info)

    # Set up TCP server
    HOST = '127.0.0.1'  # Localhost
    PORT = 5000         # Port from the provided code

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        conn, addr = server_socket.accept()
        with conn:
            while True:
                # Read the length prefix (4 bytes, uint32)
                data = conn.recv(4)
                if not data:
                    break
                length = struct.unpack('!I', data)[0]

                # Read the message
                message_data = conn.recv(length)
                if not message_data:
                    break
                message = message_data.decode('utf-8')

                # Parse the message
                parts = message.split(',')
                if len(parts) < 3:
                    continue

                sensor_type = parts[0]

                if sensor_type == 'GSR':
                    if len(parts) != 3:
                        continue
                    resistance = float(parts[2])
                    # Push to LSL (autogenerate timestamp)
                    gsr_outlet.push_sample([resistance])
                    #print(f"Pushed GSR: {resistance}")

                elif sensor_type == 'HR':
                    if len(parts) != 4:
                        continue
                    heartrate = float(parts[2])
                    quality = parts[3]
                    quality_flag = 1.0 if quality == 'Locked' else 0.0
                    # Push to LSL (autogenerate timestamp)
                    hr_outlet.push_sample([heartrate, quality_flag])
                    #print(f"Pushed HR: {heartrate}, Quality: {quality_flag}")

if __name__ == "__main__":
    start_band_receiver()