#include "detector.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>

// ncnn OMP control
#include <cpu.h>

bool NCNNDetector::load(const std::string& param_path,
                        const std::string& bin_path, int num_threads) {
    num_threads_ = num_threads;

    // Configure network options
    net_.opt.use_vulkan_compute = false;
    net_.opt.num_threads = num_threads;
    net_.opt.use_fp16_packed = true;
    net_.opt.use_fp16_storage = true;
    net_.opt.use_fp16_arithmetic = false;  // Keep FP32 math for accuracy
    net_.opt.use_packing_layout = true;

    int ret_param = net_.load_param(param_path.c_str());
    if (ret_param != 0) {
        return false;
    }

    int ret_bin = net_.load_model(bin_path.c_str());
    if (ret_bin != 0) {
        return false;
    }

    loaded_ = true;
    return true;
}

std::vector<Detection> NCNNDetector::detect(const uint8_t* data, int height,
                                            int width, int channels,
                                            float conf_threshold,
                                            float nms_threshold) {
    if (!loaded_) {
        return {};
    }

    // Set OMP threads before inference — this is the whole point of this
    // wrapper, as the Python ncnn binding has a bug where OMP threads
    // are always 1 on aarch64.
    ncnn::set_omp_num_threads(num_threads_);

    float scale = 0.0f;
    int pad_h = 0, pad_w = 0;
    ncnn::Mat input = preprocess(data, height, width, channels, scale, pad_h,
                                 pad_w);

    auto t0 = std::chrono::high_resolution_clock::now();

    // Run inference
    ncnn::Extractor ex = net_.create_extractor();
    ex.set_num_threads(num_threads_);
    ex.input("in0", input);

    ncnn::Mat output;
    ex.extract("out0", output);

    auto t1 = std::chrono::high_resolution_clock::now();
    inference_ms_ =
        std::chrono::duration<float, std::milli>(t1 - t0).count();

    return postprocess(output, scale, pad_h, pad_w, height, width,
                       conf_threshold, nms_threshold);
}

void NCNNDetector::set_num_threads(int n) {
    num_threads_ = n;
    net_.opt.num_threads = n;
}

float NCNNDetector::last_inference_ms() const {
    return inference_ms_;
}

bool NCNNDetector::is_loaded() const {
    return loaded_;
}

ncnn::Mat NCNNDetector::preprocess(const uint8_t* data, int h, int w, int c,
                                   float& scale, int& pad_h, int& pad_w) {
    // Compute letterbox scale: fit the larger dimension to INPUT_SIZE
    float scale_h = static_cast<float>(INPUT_SIZE) / h;
    float scale_w = static_cast<float>(INPUT_SIZE) / w;
    scale = std::min(scale_h, scale_w);

    int new_w = static_cast<int>(std::round(w * scale));
    int new_h = static_cast<int>(std::round(h * scale));

    // Padding to make it exactly INPUT_SIZE x INPUT_SIZE
    pad_w = (INPUT_SIZE - new_w) / 2;
    pad_h = (INPUT_SIZE - new_h) / 2;

    // Resize source to new_w x new_h (HWC uint8 -> CHW float, 0-255 range)
    ncnn::Mat resized = ncnn::Mat::from_pixels_resize(
        data, ncnn::Mat::PIXEL_RGB, w, h, new_w, new_h);

    // Create output mat filled with gray (114.0 in 0-255 space,
    // will be normalized to 0-1 after copy)
    ncnn::Mat padded(INPUT_SIZE, INPUT_SIZE, 3);
    padded.fill(114.0f);

    // Copy resized content into the padded mat at the correct offset.
    // ncnn::Mat is CHW layout: channel c has shape (new_h, new_w)
    // padded channel c has shape (INPUT_SIZE, INPUT_SIZE)
    for (int ch = 0; ch < 3; ++ch) {
        const float* src_ch = resized.channel(ch);
        float* dst_ch = padded.channel(ch);
        for (int row = 0; row < new_h; ++row) {
            const float* src_row = src_ch + row * new_w;
            float* dst_row = dst_ch + (row + pad_h) * INPUT_SIZE + pad_w;
            std::memcpy(dst_row, src_row, new_w * sizeof(float));
        }
    }

    // Normalize: from_pixels_resize produces 0-255 float values,
    // we need 0-1 range.
    const float norm_vals[3] = {1.0f / 255.0f, 1.0f / 255.0f,
                                1.0f / 255.0f};
    padded.substract_mean_normalize(nullptr, norm_vals);

    return padded;
}

std::vector<Detection> NCNNDetector::postprocess(
    const ncnn::Mat& output, float scale, int pad_h, int pad_w, int orig_h,
    int orig_w, float conf_thresh, float nms_thresh) {
    // The NCNN model output (out0) is already fully decoded:
    // Shape: [8400, 5] where each row is [cx, cy, w, h, class_score]
    // - bbox values are in 640x640 letterboxed coordinate space
    // - class_score is already sigmoid-ed
    //
    // ncnn::Mat layout: output.w = 5, output.h = 8400
    // Access: output.row(i)[j]

    std::vector<Detection> dets;
    dets.reserve(100);

    int num_proposals = output.h;
    int num_values = output.w;  // Should be 5 (4 bbox + 1 class)
    int num_classes = num_values - 4;

    for (int i = 0; i < num_proposals; ++i) {
        const float* row = output.row(i);

        // Find the best class score
        float max_score = 0.0f;
        int max_class = 0;
        for (int c = 0; c < num_classes; ++c) {
            float score = row[4 + c];
            if (score > max_score) {
                max_score = score;
                max_class = c;
            }
        }

        if (max_score < conf_thresh) {
            continue;
        }

        // Decode bbox from center-wh to xyxy in letterbox space
        float cx = row[0];
        float cy = row[1];
        float bw = row[2];
        float bh = row[3];

        float x1 = cx - bw * 0.5f;
        float y1 = cy - bh * 0.5f;
        float x2 = cx + bw * 0.5f;
        float y2 = cy + bh * 0.5f;

        // Remove letterbox padding and rescale to original image coordinates
        x1 = (x1 - pad_w) / scale;
        y1 = (y1 - pad_h) / scale;
        x2 = (x2 - pad_w) / scale;
        y2 = (y2 - pad_h) / scale;

        // Clip to image boundaries
        x1 = std::max(0.0f, std::min(x1, static_cast<float>(orig_w)));
        y1 = std::max(0.0f, std::min(y1, static_cast<float>(orig_h)));
        x2 = std::max(0.0f, std::min(x2, static_cast<float>(orig_w)));
        y2 = std::max(0.0f, std::min(y2, static_cast<float>(orig_h)));

        Detection det;
        det.class_id = max_class;
        det.confidence = max_score;
        det.x1 = x1;
        det.y1 = y1;
        det.x2 = x2;
        det.y2 = y2;
        dets.push_back(det);
    }

    nms(dets, nms_thresh);
    return dets;
}

void NCNNDetector::nms(std::vector<Detection>& dets, float threshold) {
    if (dets.empty()) {
        return;
    }

    // Sort by confidence (descending)
    std::sort(dets.begin(), dets.end(),
              [](const Detection& a, const Detection& b) {
                  return a.confidence > b.confidence;
              });

    std::vector<bool> suppressed(dets.size(), false);
    std::vector<Detection> result;
    result.reserve(dets.size());

    for (size_t i = 0; i < dets.size(); ++i) {
        if (suppressed[i]) {
            continue;
        }
        result.push_back(dets[i]);

        for (size_t j = i + 1; j < dets.size(); ++j) {
            if (suppressed[j]) {
                continue;
            }
            // Only suppress same-class detections
            if (dets[i].class_id == dets[j].class_id &&
                iou(dets[i], dets[j]) > threshold) {
                suppressed[j] = true;
            }
        }
    }

    dets = std::move(result);
}

float NCNNDetector::iou(const Detection& a, const Detection& b) {
    float inter_x1 = std::max(a.x1, b.x1);
    float inter_y1 = std::max(a.y1, b.y1);
    float inter_x2 = std::min(a.x2, b.x2);
    float inter_y2 = std::min(a.y2, b.y2);

    float inter_w = std::max(0.0f, inter_x2 - inter_x1);
    float inter_h = std::max(0.0f, inter_y2 - inter_y1);
    float inter_area = inter_w * inter_h;

    float area_a = (a.x2 - a.x1) * (a.y2 - a.y1);
    float area_b = (b.x2 - b.x1) * (b.y2 - b.y1);
    float union_area = area_a + area_b - inter_area;

    if (union_area <= 0.0f) {
        return 0.0f;
    }
    return inter_area / union_area;
}
