# Dataset Preparation

🇷🇺 [Русская версия](../ru/dataset.md)

To train a sock detection model you need a labeled dataset — a set of photos with bounding boxes marking where the socks are in each image.

## Capturing photos

### Running the camera

Photos are captured directly from the Raspberry Pi camera. The script takes a series of shots with pauses so you can reposition the sock:

```bash
# On Raspberry Pi (requires sudo for camera access)
sudo ./main.py shot --count 200 --output-dir images
```

Parameters:
- `--count` — number of shots (default 200)
- `--output-dir` — output folder (default `images/`)
- `--pause` — pause between shots in seconds (default 2)
- `--move-pause` — pause every 10 shots to reposition the sock (default 10)

### Tips for capturing

- **Variety of angles**: capture socks from different sides, at different distances from the camera
- **Different lighting**: daylight, artificial light, shadows
- **Different surfaces**: floor, carpet, under furniture, on a couch
- **Different socks**: various colors, sizes, folded and unfolded
- **Background**: capture in real apartment conditions, not on a plain background
- **Quantity**: more is better. Minimum 200 photos, optimal — 500+

## Uploading to Roboflow

[Roboflow](https://roboflow.com/) is a platform for managing computer vision datasets. The free tier covers all our needs.

1. Sign up at [roboflow.com](https://roboflow.com/)
2. Create a new project: **Object Detection**, 1 class — `sock`
3. Upload all photos (Upload Data)

<img width="850" height="516" alt="Uploading data to Roboflow" src="https://github.com/user-attachments/assets/38e06e59-6363-4463-808c-71c0722c2f65" />

## Annotation (labeling)

On each photo you need to draw a bounding box (rectangle) around every sock and assign the class `sock`.

Roboflow provides a built-in annotation editor:
- Select the **Bounding Box** tool
- Draw a box around each sock in the photo
- Assign class `sock`
- Repeat for all photos

<img width="1410" height="640" alt="Annotating data in Roboflow" src="https://github.com/user-attachments/assets/97fa19b5-90dc-43c5-ba80-8735d1ed30c9" />

> **Tip**: if a sock is partially hidden (e.g., under a chair), still annotate the visible part. The model will learn to recognize partially visible socks.

## Augmentation

Augmentation automatically creates image variations to increase the dataset. Roboflow can apply:

- **Rotation** — random rotation ±15°
- **Crop** — random crop up to 10% from each side
- **Brightness** — brightness change ±20%
- **Blur** — slight blur (up to 2.5 px)
- **Noise** — adding noise (up to 3%)

When creating a new dataset version (Create New Version) Roboflow applies the selected augmentations and increases the number of training images.

<img width="1406" height="439" alt="Creating a version with augmentation" src="https://github.com/user-attachments/assets/02dc7c54-c0b4-49e0-9636-459974bde62a" />

Quick rule of thumb:
- use **Roboflow** if you want the fastest path from photos to a trainable dataset;
- use **`albumentations`** if you want a reproducible, code-based augmentation pipeline.

### Alternative: local augmentation via Python (`albumentations`)

If you want a reproducible local pipeline instead of Roboflow, a common choice is [`albumentations`](https://albumentations.ai/). It is widely used for computer vision and supports bounding boxes.

Install:

```bash
pip install albumentations opencv-python
```

Example augmentation pipeline for a YOLO-style dataset:

```python
import cv2
import albumentations as A

transform = A.Compose(
    [
        A.Rotate(limit=15, border_mode=cv2.BORDER_CONSTANT, p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
        A.GaussianBlur(blur_limit=(3, 5), p=0.2),
        A.GaussNoise(std_range=(0.02, 0.08), p=0.2),
        A.RandomCropFromBorders(crop_left=0.1, crop_right=0.1, crop_top=0.1, crop_bottom=0.1, p=0.2),
    ],
    bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
)

image = cv2.imread("dataset/train/images/example.jpg")
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

bboxes = [
    [0.52, 0.48, 0.30, 0.22],  # x_center, y_center, width, height (YOLO format)
]
class_labels = ["sock"]

augmented = transform(image=image, bboxes=bboxes, class_labels=class_labels)
augmented_image = augmented["image"]
augmented_bboxes = augmented["bboxes"]
```

When this approach is useful:

- you want reproducible augmentations in code
- you need to version-control the augmentation pipeline
- you want to run the same transforms locally, in notebooks, or in CI

For this project, Roboflow is still the fastest path for dataset management, but `albumentations` is a good alternative if you prefer a code-based workflow.

## Exporting the dataset

After creating a version — download the dataset in **YOLOv8** format:

1. Click **Download Dataset**
2. Select format **YOLOv8**
3. Choose **download zip to computer** or **show download code**

<img width="813" height="438" alt="Selecting YOLOv8 format for download" src="https://github.com/user-attachments/assets/694745a3-ed5e-4e44-96f5-8b866a6f5837" />

Or download via terminal:

```bash
curl -L "https://app.roboflow.com/ds/YOUR_DATASET_URL" > roboflow.zip
unzip roboflow.zip
rm roboflow.zip
```

## Dataset structure

After extraction the dataset has the following structure:

```
dataset/
├── train/
│   ├── images/        # Training images (~70%)
│   └── labels/        # Annotations in YOLO format (txt)
├── valid/
│   ├── images/        # Validation images (~20%)
│   └── labels/
├── test/
│   ├── images/        # Test images (~10%)
│   └── labels/
└── data.yaml          # Dataset config
```

The `data.yaml` file describes paths and classes:

```yaml
train: dataset/train/images
val: dataset/valid/images
test: dataset/test/images

nc: 1
names: ['sock']
```

The current dataset version contains **961 images** (Roboflow workspace: `socks-axfcs`, project: `socks1`, version 2).

---

| ← Previous | README | Next → |
|---|---|---|
| [Raspberry Pi 4 Setup (legacy)](rpi4.md) | [Back to README](README.md) | [Model Training](training.md) |
