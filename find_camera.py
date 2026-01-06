import cv2
import time

# Suppress OpenCV warnings for cleaner output
import os
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
cv2.setLogLevel(0)

print("Checking video devices with thorough validation...")
print("-" * 40)

for i in range(16):
    cap = cv2.VideoCapture(i)
    if not cap.isOpened():
        print(f"✗ Device {i}: Cannot open")
        continue

    try:
        # Give camera time to initialize
        time.sleep(0.2)

        # Try to set properties (real cameras accept this, metadata devices often don't)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Test by reading multiple frames
        # (metadata devices on Linux often open but can't stream)
        successful_reads = 0
        first_frame = None

        for _ in range(5):
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                if first_frame is None:
                    first_frame = frame
                successful_reads += 1
            time.sleep(0.05)

        if successful_reads >= 3:
            resolution = f"{first_frame.shape[1]}x{first_frame.shape[0]}"
            print(f"✓ Device {i}: Working (Resolution: {resolution}, {successful_reads}/5 frames read)")
        else:
            print(f"✗ Device {i}: Opened but unreliable ({successful_reads}/5 frames read) - likely metadata device")

    except Exception as e:
        print(f"✗ Device {i}: Error during testing ({str(e)})")
    finally:
        cap.release()

print("-" * 40)
print("Use the device number marked with ✓ in your app")
