import time
from picamera2 import Picamera2
from libcamera import Transform


cam = Picamera2()

config = cam.create_still_configuration(
    main={"size": (1920, 1080)}, transform=Transform(vflip=True)
)
cam.configure(config)

cam.start()

for i in range(200):
    print(f"Iter {i}")
    if i % 10 == 0:
        print("Move to next sock... Sleep 10 seconds")
        time.sleep(10)
    else:
        time.sleep(2)
    cam.capture_file(f"images/image{i}.jpg")

cam.stop()
