// Stub for the SDK's quality-reference ISP entry point.
//
// The full SDK ships libCyperlib.a (fast_isp.cc + the HDR-ISP pipeline under
// src/ISP/...) which implements cyperstereo::detail::ApplyQualityReferenceISPParallel.
// This ORB-SLAM3 build links only the V4L2 backend (Cyperlib) and uses the
// header-only fast-balanced ISP (IspMode::kFastBalancedBgr888), so the quality
// path is never taken.  The symbol is still referenced by
// IspProcessor::ApplyParallel's quality branch, so define it here to satisfy
// the linker rather than dragging in the whole HDR-ISP tree.
#include <opencv2/core/core.hpp>

#include "../../Thirdparty/usb/uvc/cyperstereo_api.h"

namespace cyperstereo {
namespace detail {

void ApplyQualityReferenceISPParallel(
    const cv::Mat *const * /*raws*/, cv::Mat *const * /*outputs*/,
    const char *const * /*names*/, const double * /*sensor_gains*/,
    const BayerConversion * /*bayers*/, int /*n*/) {
  throw std::runtime_error(
      "quality-reference ISP is not linked into this build; "
      "use IspMode::kFastBalancedBgr888");
}

}  // namespace detail
}  // namespace cyperstereo
