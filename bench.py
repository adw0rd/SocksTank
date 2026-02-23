from ultralytics.utils.benchmarks import benchmark

# Benchmark on GPU
benchmark(model="yolov8n.pt", data="data.yaml", imgsz=640, half=False, device=0)
