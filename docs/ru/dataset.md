# Подготовка датасета

🇬🇧 [English version](../en/dataset.md)

Для обучения модели распознавания носков нужен размеченный датасет — набор фотографий с указанием, где именно на каждом снимке находятся носки (bounding box).

## Съёмка фотографий

### Запуск камеры

Фотографии снимаются напрямую с камеры Raspberry Pi. Скрипт делает серию снимков с паузами, чтобы успеть переложить носок в новое положение:

```bash
# На Raspberry Pi (требует sudo для доступа к камере)
sudo ./main.py shot --count 200 --output-dir images
```

Параметры:
- `--count` — количество снимков (по умолчанию 200)
- `--output-dir` — папка для сохранения (по умолчанию `images/`)
- `--pause` — пауза между снимками в секундах (по умолчанию 2)
- `--move-pause` — пауза каждые 10 снимков для смены позиции носка (по умолчанию 10)

### Советы по съёмке

- **Разнообразие ракурсов**: снимайте носки с разных сторон, на разном расстоянии от камеры
- **Разное освещение**: при дневном свете, при искусственном, в тени
- **Разные поверхности**: на полу, ковре, под мебелью, на диване
- **Разные носки**: разных цветов, размеров, сложенные и разложенные
- **Фон**: снимайте в реальных условиях квартиры, а не на однотонном фоне
- **Количество**: чем больше, тем лучше. Минимум 200 фото, оптимально — 500+

## Загрузка в Roboflow

[Roboflow](https://roboflow.com/) — платформа для управления датасетами компьютерного зрения. Бесплатный тариф покрывает все наши потребности.

1. Зарегистрироваться на [roboflow.com](https://roboflow.com/)
2. Создать новый проект: **Object Detection**, 1 класс — `sock`
3. Загрузить все фотографии (Upload Data)

<img width="850" height="516" alt="Загрузка данных в Roboflow" src="https://github.com/user-attachments/assets/38e06e59-6363-4463-808c-71c0722c2f65" />

## Аннотирование (разметка)

На каждой фотографии нужно отметить bounding box (прямоугольник) вокруг каждого носка и присвоить ему класс `sock`.

Roboflow предоставляет встроенный редактор для разметки:
- Выбрать инструмент **Bounding Box**
- Обвести каждый носок на фотографии
- Указать класс `sock`
- Повторить для всех фотографий

<img width="1410" height="640" alt="Разметка данных в Roboflow" src="https://github.com/user-attachments/assets/97fa19b5-90dc-43c5-ba80-8735d1ed30c9" />

> **Совет**: если носок частично скрыт (например, под стулом), всё равно размечайте видимую часть. Модель научится распознавать и частично видимые носки.

## Аугментация

Аугментация — автоматическое создание вариаций изображений для увеличения датасета. Roboflow может:

- **Повороты** — случайный поворот на ±15°
- **Обрезка** — случайная обрезка до 10% с каждой стороны
- **Яркость** — изменение яркости ±20%
- **Размытие** — лёгкое размытие (до 2.5 px)
- **Шум** — добавление шума (до 3%)

При создании новой версии датасета (Create New Version) Roboflow применит выбранные аугментации и увеличит количество изображений в тренировочной выборке.

<img width="1406" height="439" alt="Создание версии с аугментацией" src="https://github.com/user-attachments/assets/02dc7c54-c0b4-49e0-9636-459974bde62a" />

Быстрое правило:
- **Roboflow** — если нужен самый быстрый путь от фотографий к готовому trainable-датасету;
- **`albumentations`** — если нужен воспроизводимый pipeline аугментации через код.

### Альтернатива: локальная аугментация через Python (`albumentations`)

Если нужен воспроизводимый локальный pipeline вместо Roboflow, популярный вариант — [`albumentations`](https://albumentations.ai/). Эта библиотека широко используется в computer vision и умеет работать с bounding box'ами.

Установка:

```bash
pip install albumentations opencv-python
```

Пример augmentation pipeline для датасета в стиле YOLO:

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
    [0.52, 0.48, 0.30, 0.22],  # x_center, y_center, width, height (формат YOLO)
]
class_labels = ["sock"]

augmented = transform(image=image, bboxes=bboxes, class_labels=class_labels)
augmented_image = augmented["image"]
augmented_bboxes = augmented["bboxes"]
```

Когда это удобно:

- если нужны воспроизводимые аугментации в коде
- если хочется version-control для augmentation pipeline
- если нужно запускать одинаковые преобразования локально, в ноутбуках или в CI

Для этого проекта Roboflow по-прежнему самый быстрый путь для управления датасетом, но `albumentations` — хороший вариант, если тебе ближе workflow через код.

## Экспорт датасета

После создания версии — скачать датасет в формате **YOLOv8**:

1. Нажать **Download Dataset**
2. Выбрать формат **YOLOv8**
3. Выбрать **download zip to computer** или **show download code**

<img width="813" height="438" alt="Выбор формата YOLOv8 при скачивании" src="https://github.com/user-attachments/assets/694745a3-ed5e-4e44-96f5-8b866a6f5837" />

Или скачать через терминал:

```bash
curl -L "https://app.roboflow.com/ds/YOUR_DATASET_URL" > roboflow.zip
unzip roboflow.zip
rm roboflow.zip
```

## Структура датасета

После распаковки датасет имеет следующую структуру:

```
dataset/
├── train/
│   ├── images/        # Тренировочные изображения (~70%)
│   └── labels/        # Аннотации в формате YOLO (txt)
├── valid/
│   ├── images/        # Валидационные изображения (~20%)
│   └── labels/
├── test/
│   ├── images/        # Тестовые изображения (~10%)
│   └── labels/
└── data.yaml          # Конфиг датасета
```

Файл `data.yaml` описывает пути и классы:

```yaml
train: dataset/train/images
val: dataset/valid/images
test: dataset/test/images

nc: 1
names: ['sock']
```

В текущей версии датасета — **961 изображение** (Roboflow workspace: `socks-axfcs`, project: `socks1`, version 2).

---

| ← Предыдущая | README | Следующая → |
|---|---|---|
| [Настройка Raspberry Pi 4 (legacy)](rpi4.md) | [Вернуться к README](README.md) | [Тренировка модели](training.md) |
