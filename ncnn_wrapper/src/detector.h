#pragma once

#include <string>
#include <vector>

#include <net.h>

/// Single detected object with class id, confidence, and bounding box.
struct Detection {
    int class_id;
    float confidence;
    float x1, y1, x2, y2;  // bbox in original image coordinates
};

/// NCNN-based YOLO detector with proper OMP thread control.
///
/// This wrapper exists because the Python ncnn binding has an OMP bug
/// on aarch64 (pip ncnn 1.0.x for cp313): get_omp_num_threads() always
/// returns 1 regardless of settings. The C++ ncnn library works correctly.
class NCNNDetector {
public:
    NCNNDetector() = default;
    ~NCNNDetector() = default;

    // Non-copyable (ncnn::Net has internal state)
    NCNNDetector(const NCNNDetector&) = delete;
    NCNNDetector& operator=(const NCNNDetector&) = delete;

    /// Load NCNN model from .param and .bin files.
    /// @param param_path  Path to model.ncnn.param
    /// @param bin_path    Path to model.ncnn.bin
    /// @param num_threads Number of OMP threads for inference (default 2)
    /// @return true on success
    bool load(const std::string& param_path, const std::string& bin_path,
              int num_threads = 2);

    /// Run detection on a raw image buffer (HWC, uint8).
    /// @param data           Pointer to pixel data (RGB or BGR, HWC layout)
    /// @param height         Image height
    /// @param width          Image width
    /// @param channels       Number of channels (3 for RGB/BGR)
    /// @param conf_threshold Confidence threshold for filtering detections
    /// @param nms_threshold  IoU threshold for non-maximum suppression
    /// @return Vector of detections with coordinates in original image space
    std::vector<Detection> detect(const uint8_t* data, int height, int width,
                                  int channels, float conf_threshold = 0.5f,
                                  float nms_threshold = 0.45f);

    /// Set number of OMP threads for subsequent inference calls.
    void set_num_threads(int n);

    /// Get the inference time of the last detect() call in milliseconds.
    float last_inference_ms() const;

    /// Check if the model has been loaded successfully.
    bool is_loaded() const;

private:
    ncnn::Net net_;
    int num_threads_ = 2;
    float inference_ms_ = 0.0f;
    bool loaded_ = false;

    // Input size expected by the model
    static constexpr int INPUT_SIZE = 640;

    /// Letterbox-resize and normalize the input image to 640x640.
    /// Returns the preprocessed ncnn::Mat and sets scale/padding info
    /// needed to map detections back to original coordinates.
    ncnn::Mat preprocess(const uint8_t* data, int h, int w, int c,
                         float& scale, int& pad_h, int& pad_w);

    /// Decode YOLO output tensor into detections.
    /// The NCNN model output is [8400, 5]: 4 decoded bbox values (cx, cy, w, h
    /// already multiplied by stride) + 1 sigmoid class score.
    std::vector<Detection> postprocess(const ncnn::Mat& output, float scale,
                                       int pad_h, int pad_w, int orig_h,
                                       int orig_w, float conf_thresh,
                                       float nms_thresh);

    /// Standard IoU-based non-maximum suppression.
    static void nms(std::vector<Detection>& dets, float threshold);

    /// Compute intersection-over-union between two boxes.
    static float iou(const Detection& a, const Detection& b);
};
