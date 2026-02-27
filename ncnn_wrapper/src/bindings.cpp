#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "detector.h"

namespace py = pybind11;

/// Python wrapper for NCNNDetector.detect() that accepts numpy arrays
/// and returns a list of dicts compatible with the SocksTank detection format.
static py::list detect_numpy(NCNNDetector& self, py::array_t<uint8_t> image,
                             float conf_threshold, float nms_threshold) {
    auto buf = image.request();

    // Validate numpy array shape: (H, W, C)
    if (buf.ndim != 3) {
        throw std::runtime_error(
            "Expected 3D array (H, W, C), got " +
            std::to_string(buf.ndim) + "D");
    }

    int height = static_cast<int>(buf.shape[0]);
    int width = static_cast<int>(buf.shape[1]);
    int channels = static_cast<int>(buf.shape[2]);

    if (channels != 3) {
        throw std::runtime_error(
            "Expected 3 channels (RGB), got " + std::to_string(channels));
    }

    // Ensure contiguous C-order array
    if (buf.strides[2] != sizeof(uint8_t) ||
        buf.strides[1] != channels * sizeof(uint8_t) ||
        buf.strides[0] != width * channels * sizeof(uint8_t)) {
        throw std::runtime_error("Array must be contiguous (C-order)");
    }

    const auto* data = static_cast<const uint8_t*>(buf.ptr);
    auto detections = self.detect(data, height, width, channels,
                                  conf_threshold, nms_threshold);

    // Convert to list of dicts matching SocksTank format:
    // [{"class_id": 0, "confidence": 0.92, "bbox": [x1, y1, x2, y2]}, ...]
    py::list result;
    for (const auto& det : detections) {
        py::dict d;
        d["class_id"] = det.class_id;
        d["confidence"] = det.confidence;
        d["bbox"] = py::make_tuple(
            static_cast<int>(det.x1), static_cast<int>(det.y1),
            static_cast<int>(det.x2), static_cast<int>(det.y2));
        result.append(d);
    }
    return result;
}

PYBIND11_MODULE(ncnn_wrapper, m) {
    m.doc() = "C++ NCNN inference wrapper for SocksTank YOLO detector. "
              "Bypasses the Python ncnn OMP thread bug on aarch64.";

    py::class_<NCNNDetector>(m, "NCNNDetector")
        .def(py::init<>())
        .def("load", &NCNNDetector::load,
             py::arg("param_path"), py::arg("bin_path"),
             py::arg("num_threads") = 2,
             "Load NCNN model from .param and .bin files")
        .def("detect", &detect_numpy,
             py::arg("image"), py::arg("conf_threshold") = 0.5f,
             py::arg("nms_threshold") = 0.45f,
             "Run detection on a numpy image array (H, W, 3) uint8 RGB. "
             "Returns list of dicts with class_id, confidence, bbox.")
        .def("set_num_threads", &NCNNDetector::set_num_threads,
             py::arg("n"),
             "Set number of OMP threads for inference")
        .def("last_inference_ms", &NCNNDetector::last_inference_ms,
             "Get inference time of last detect() call in milliseconds")
        .def("is_loaded", &NCNNDetector::is_loaded,
             "Check if model is loaded")
        .def("__repr__", [](const NCNNDetector& d) {
            return "<NCNNDetector loaded=" +
                   std::string(d.is_loaded() ? "true" : "false") + ">";
        });
}
