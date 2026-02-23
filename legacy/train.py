from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.info()

results = model.train(data="data.yaml", epochs=100, imgsz=640)

print(results)
