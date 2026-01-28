import sys
from pathlib import Path
import time
from datetime import datetime
import numpy as np
import pylsl

# ── CONFIG ──────────────────────────────────────────────
FRIENDLY_NAME = "EngagementExperiment_LSL"

USE_UNIFIED_VIEWPORT = True
SCREEN_WIDTH_PX = 1920
SCREEN_HEIGHT_PX = 1080

LSL_STREAM_NAME = "BeamEyeTracker_GazeHead_Matrix"
LSL_STREAM_TYPE = "GazeHead"
LSL_SOURCE_ID = "beam"
LSL_NOMINAL_SRATE = 60.0
# ────────────────────────────────────────────────────────

sdk_path = Path(__file__).parent / "beam_eye_tracker_sdk" / "beam_eye_tracker_sdk-2.1.0" / "python" / "package"
sys.path.append(str(sdk_path))

from eyeware.beam_eye_tracker import (
    API,
    ViewportGeometry,
    Point,
    TrackingListener,
    NULL_DATA_TIMESTAMP,
)
def start_beam_stream():
    # Viewport
    if USE_UNIFIED_VIEWPORT:
        viewport = ViewportGeometry(Point(0.0, 0.0), Point(1.0, 1.0))
        print("Using unified (normalized 0–1) viewport")
    else:
        viewport = ViewportGeometry(Point(0, 0), Point(SCREEN_WIDTH_PX, SCREEN_HEIGHT_PX))
        print(f"Using pixel viewport: {SCREEN_WIDTH_PX} × {SCREEN_HEIGHT_PX}")

    # LSL setup – 16 channels (data values only – no timestamp in sample)
    outlet_info = pylsl.StreamInfo(LSL_STREAM_NAME, LSL_STREAM_TYPE, 16, LSL_NOMINAL_SRATE, 'float32', LSL_SOURCE_ID)
    outlet_info.desc().append_child_value("manufacturer", "Eyeware Beam")
    channels = outlet_info.desc().append_child("channels")

    ch_names = [
        "gaze_conf_int",
        "gaze_por_x",
        "gaze_por_y",
        "head_conf_int",
        "head_pos_x_m",
        "head_pos_y_m",
        "head_pos_z_m",
        "rot_m11", "rot_m12", "rot_m13",
        "rot_m21", "rot_m22", "rot_m23",
        "rot_m31", "rot_m32", "rot_m33"
    ]

    for name in ch_names:
        ch = channels.append_child("channel")
        ch.append_child_value("label", name)

    outlet = pylsl.StreamOutlet(outlet_info)
    print(f"LSL stream: '{LSL_STREAM_NAME}' ({LSL_STREAM_TYPE}) – 16 channels")

    class TrackingLogger(TrackingListener):
        def on_tracking_state_set_update(self, tracking_state_set, timestamp):
            ts_val = timestamp.value

            user = tracking_state_set.user_state()
            if user.timestamp_in_seconds.value == NULL_DATA_TIMESTAMP().value:
                print(f"[{datetime.now().isoformat(timespec='milliseconds')}] NULL timestamp – skipping")
                return

            gaze = user.unified_screen_gaze
            head = user.head_pose

            now_iso = datetime.now().isoformat(timespec='milliseconds')

            # Gaze
            gaze_conf_int = gaze.confidence
            if gaze_conf_int == 0:
                por_x = por_y = float('nan')
            else:
                por_x = gaze.point_of_regard.x
                por_y = gaze.point_of_regard.y

            # Head position & rotation matrix
            head_conf_int = head.confidence

            if head_conf_int == 0:
                head_pos_x = head_pos_y = head_pos_z = float('nan')
                rot_flat = [float('nan')] * 9
            else:
                pos = head.translation_from_hcs_to_wcs
                head_pos_x, head_pos_y, head_pos_z = pos.x, pos.y, pos.z

                rot_mat = head.rotation_from_hcs_to_wcs  # 3×3 numpy array
                rot_flat = rot_mat.flatten().tolist()    # 9 elements

            # LSL sample – 16 floats
            sample = [
                float(gaze_conf_int),
                por_x if gaze_conf_int != 0 else 0.0,
                por_y if gaze_conf_int != 0 else 0.0,
                float(head_conf_int),
                head_pos_x if head_conf_int != 0 else 0.0,
                head_pos_y if head_conf_int != 0 else 0.0,
                head_pos_z if head_conf_int != 0 else 0.0,
            ] + rot_flat
            outlet.push_sample(sample)  # LSL auto-timestamps

            # Live print
            '''print(f"[{now_iso}] ts={ts_val:.2f}s | "
                f"Gaze conf {gaze_conf_int} POR ({por_x:.4f}, {por_y:.4f}) | "
                f"Head conf {head_conf_int} Pos ({head_pos_x:.3f}, {head_pos_y:.3f}, {head_pos_z:.3f}m) "
                f"Matrix sample: {rot_flat[:3]} ...")
            '''
        def on_tracking_data_reception_status_changed(self, status):
            print(f"Tracking reception status: {status}")

    # ── Main ────────────────────────────────────────────────
    api = API(FRIENDLY_NAME, viewport)
    api.attempt_starting_the_beam_eye_tracker()

    listener = TrackingLogger()
    handle = api.start_receiving_tracking_data_on_listener(listener)

    print("\nActive. Press Ctrl+C to stop.")
    print(f"LSL: '{LSL_STREAM_NAME}' – 16 channels (data values only)")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        api.stop_receiving_tracking_data_on_listener(handle)
        print("Done.")

if __name__ == "__main__":
    start_beam_stream()