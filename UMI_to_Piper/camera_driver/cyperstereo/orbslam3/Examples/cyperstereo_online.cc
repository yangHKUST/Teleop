#include <chrono>
#include <condition_variable>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <fstream>
#include <iostream>
#include <mutex>
#include "string"
#include <queue>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/imgcodecs/imgcodecs.hpp>

#include <array>
#include "../../Thirdparty/usb/uvc/cyperstereo_api.h"
#include "Thirdparty/usb/uvc/uvc.h"
#include "Thirdparty/usb/uvc/tic_toc.h"

#include <System.h>
#include <Eigen/Dense>
#include <thread>

#include <zmq.h>
#include <cstdio>
#include <cstdlib>

const double g = 9.7887;

CYPERSTEREO_USE_NAMESPACE
std::queue<pair<double,std::vector<Eigen::Vector3d>> > IMU;
std::queue<pair<double,std::vector<cv::Mat>> > IMAGE;
std::mutex m_buf;
double current_time = -1;
std::condition_variable con;
ORB_SLAM3::System *SLAM;

// --- VIO pose bridge (scheme A: ZMQ PUB -> ROS2 /vio/odom) ---
void* g_zmq_ctx = nullptr;         // ZMQ context
void* g_pose_socket = nullptr;     // ZMQ PUB socket (null if unavailable)
void* g_img_socket = nullptr;      // ZMQ PUB socket for stereo image bridge
constexpr double kMinImuInitAgeSec = 1.0;  // don't publish until this long after IMU init
constexpr int    kTrackingOk = 2;          // Tracking::eTrackingState::OK

constexpr double kMaxGyroRadS = 50.0;   // generous bound to drop corrupted samples
constexpr double kMaxAccMS2 = 200.0;    // generous bound to drop corrupted samples


void InputIMU( const double timestamp, const Eigen::Vector3d& accl, const Eigen::Vector3d& gyro)
{
    m_buf.lock();
    std::vector<Eigen::Vector3d> imu_temp;
    imu_temp.push_back(accl);
    imu_temp.push_back(gyro);
    IMU.push(make_pair(timestamp,imu_temp));
    m_buf.unlock();
    con.notify_one();
}

void InputImage(const cv::Mat& cam0_img,
                const cv::Mat& cam1_img,
                double time)
{
    m_buf.lock();
    std::vector<cv::Mat> image_temp;
    image_temp.push_back(cam0_img);
    image_temp.push_back(cam1_img);
    IMAGE.push(make_pair(time,image_temp));
    m_buf.unlock();
    con.notify_one();

}


std::vector<std::pair<std::vector<std::pair<double,std::vector<Eigen::Vector3d>> >, std::vector<std::pair<double,std::vector<cv::Mat>> > >>
getMeasurements()
{
    std::vector<std::pair<std::vector<std::pair<double,std::vector<Eigen::Vector3d>> >, std::vector<std::pair<double,std::vector<cv::Mat>> > >>  measurements;
    while (true)
    {

        if(IMAGE.empty()||IMU.empty())
        {
          //cout<<"wait for data"<<endl;
          return measurements;
        }

        if (!(IMU.back().first > IMAGE.front().first))
        {
            // cout<<"wait for imu, only should happen at the beginning";
            { // ---- temporary IMU diagnostics ----
              static int dbg_wait = 0;
              if (dbg_wait < 20) {
                std::cerr << "[dbg] getMeas wait-imu: imu_back=" << IMU.back().first
                          << " img_front=" << IMAGE.front().first
                          << " imu_front=" << IMU.front().first << std::endl;
                ++dbg_wait;
              }
            }
            return measurements;
        }
        if (!(IMU.front().first < IMAGE.front().first))
        {
            cout<<"throw img, only should happen at the beginning";
            IMAGE.pop();
            continue;
        }
        std::vector<std::pair<double,std::vector<Eigen::Vector3d>> > IMUs;
        while (IMU.front().first < IMAGE.front().first)
        {
            IMUs.emplace_back(IMU.front());
            IMU.pop();
        }
        IMUs.emplace_back(IMU.front());

        if (IMUs.empty())
           cout<<"no imu between two image";

        vector<pair<double,std::vector<cv::Mat>> > IMAGES;
        IMAGES.push_back(IMAGE.front());
        IMAGE.pop();
        measurements.push_back(make_pair(IMUs,IMAGES));

    }
    cout<<measurements.size()<<endl;
    return measurements;
}

// Publish one 6-DOF pose over ZMQ PUB for the ROS2 /vio/odom bridge.
// Message is a single line: "<timestamp> <tx> <ty> <tz> <qx> <qy> <qz> <qw>".
// q is the camera->world rotation (R_wc); t is the camera position in the VIO
// world frame (gravity-aligned, Z up after IMU init).
void PublishPose(double timestamp,
                 double tx, double ty, double tz,
                 double qx, double qy, double qz, double qw)
{
    if (!g_pose_socket) return;
    char buf[256];
    int n = snprintf(buf, sizeof(buf), "%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f",
                     timestamp, tx, ty, tz, qx, qy, qz, qw);
    if (n <= 0 || n >= static_cast<int>(sizeof(buf))) return;
    zmq_send(g_pose_socket, buf, static_cast<size_t>(n), 0);
}

// Publish the stereo color pair over ZMQ PUB for the ROS2 vio_image_bridge.
// Multipart message:
//   part0: 8-byte double (camera image timestamp, device clock)
//   part1: left  eye JPEG bytes (left_color  -> /cam0/image_raw)
//   part2: right eye JPEG bytes (right_color -> /cam1/image_raw)
void PublishStereoImage(double timestamp,
                        const cv::Mat& left_color,
                        const cv::Mat& right_color)
{
    if (!g_img_socket) return;
    if (left_color.empty() || right_color.empty()) return;

    // Downscale the monitor feed before JPEG so the full-res encode (~1.3 MP
    // per eye) + ZMQ transfer + Rerun render don't starve the capture loop.
    // The SLAM path keeps using the full-res mats; only these copies shrink.
    const int kMaxFeedWidth = 640;
    cv::Mat l, r;
    if (left_color.cols > kMaxFeedWidth) {
        double s = static_cast<double>(kMaxFeedWidth) / left_color.cols;
        cv::resize(left_color, l, cv::Size(), s, s, cv::INTER_AREA);
        cv::resize(right_color, r, cv::Size(), s, s, cv::INTER_AREA);
    } else {
        l = left_color;
        r = right_color;
    }

    std::vector<uchar> left_jpg, right_jpg;
    // JPEG quality 85: good enough for a monitor feed, keeps ZMQ frames small.
    std::vector<int> params = {cv::IMWRITE_JPEG_QUALITY, 85};
    cv::imencode(".jpg", l, left_jpg, params);
    cv::imencode(".jpg", r, right_jpg, params);
    if (left_jpg.empty() || right_jpg.empty()) return;

    zmq_send(g_img_socket, &timestamp, sizeof(timestamp), ZMQ_SNDMORE);
    zmq_send(g_img_socket, left_jpg.data(), left_jpg.size(), ZMQ_SNDMORE);
    zmq_send(g_img_socket, right_jpg.data(), right_jpg.size(), 0);
}

void process()
{
    double last_img_t = -1.0;
    double last_imu_t = -1.0;
    while (true)
       {
        std::vector<std::pair<std::vector<std::pair<double,std::vector<Eigen::Vector3d>> >, std::vector<std::pair<double,std::vector<cv::Mat>> > >> measurements;
        std::unique_lock<std::mutex> lk(m_buf);
        con.wait(lk, [&]
                 {
            return (measurements = getMeasurements()).size() != 0;
                 });
        lk.unlock();
        
        for (auto &measurement : measurements)
        {
           std::vector<ORB_SLAM3::IMU::Point> vImuMeas;
           vImuMeas.clear();
           auto img = measurement.second.front();
           if (!std::isfinite(img.first)) {
             std::cerr << "skip image with non-finite timestamp in process()" << std::endl;
             continue;
           }
           if (last_img_t >= 0.0 && img.first <= last_img_t) {
             std::cerr << "skip non-monotonic image timestamp in process() "
                       << std::setprecision(6) << img.first << " <= " << last_img_t << std::endl;
             continue;
           }
           double dx = 0, dy = 0, dz = 0, rx = 0, ry = 0, rz = 0;
           for (auto &imu_msg : measurement.first) {
               double t = imu_msg.first;
               double img_t = img.first;
               if (!std::isfinite(t)) {
                   std::cerr << "skip imu with non-finite timestamp in process()" << std::endl;
                   continue;
               }
               if (last_imu_t >= 0.0 && t <= last_imu_t) {
                   //std::cerr << "skip non-monotonic imu timestamp in process() "
                    //         << std::setprecision(6) << t << " <= " << last_imu_t << std::endl;
                   continue;
               }
               if (t <= img_t)
               {
                   if (current_time < 0)
                       current_time = t;
                   double dt = t - current_time;
                   current_time = t;
                   dx = imu_msg.second.front()[0];
                   dy = imu_msg.second.front()[1];
                   dz = imu_msg.second.front()[2];
                   rx = imu_msg.second.back()[0];
                   ry = imu_msg.second.back()[1];
                   rz = imu_msg.second.back()[2];
                   if (std::isfinite(dx) && std::isfinite(dy) && std::isfinite(dz) &&
                       std::isfinite(rx) && std::isfinite(ry) && std::isfinite(rz) &&
                       std::abs(rx) <= kMaxGyroRadS && std::abs(ry) <= kMaxGyroRadS && std::abs(rz) <= kMaxGyroRadS &&
                       std::abs(dx) <= kMaxAccMS2 && std::abs(dy) <= kMaxAccMS2 && std::abs(dz) <= kMaxAccMS2) {
                     vImuMeas.push_back(ORB_SLAM3::IMU::Point(dx, dy, dz, rx, ry, rz, current_time));
                     last_imu_t = t;
                   } else {
                     std::cerr << "skip imu sample with invalid values in process()" << std::endl;
                   }
                  // std::cout.setf(std::ios::fixed, std::ios::floatfield);
                  // std::cout.precision(6);
                  // cout<<"imu: "<< current_time << " " << dx << " " << dy << " " << dz <<  " " << rx << " " << ry << " " << rz <<endl;

               }
               else
               {
                   double dt_1 = img_t - current_time;
                   double dt_2 = t - img_t;
                   double denom = dt_1 + dt_2;
                   if (!std::isfinite(denom) || denom <= 0.0) {
                     std::cerr << "skip imu interpolation with invalid denom in process()" << std::endl;
                     continue;
                   }
                   current_time = img_t;
                   double w1 = dt_2 / denom;
                   double w2 = dt_1 / denom;
                   dx = w1 * dx + w2 * imu_msg.second.front()[0];
                   dy = w1 * dy + w2 * imu_msg.second.front()[1];
                   dz = w1 * dz + w2 * imu_msg.second.front()[2];
                   rx = w1 * rx + w2 * imu_msg.second.back()[0];
                   ry = w1 * ry + w2 * imu_msg.second.back()[1];
                   rz = w1 * rz + w2 * imu_msg.second.back()[2];
                   if (std::isfinite(dx) && std::isfinite(dy) && std::isfinite(dz) &&
                       std::isfinite(rx) && std::isfinite(ry) && std::isfinite(rz) &&
                       std::abs(rx) <= kMaxGyroRadS && std::abs(ry) <= kMaxGyroRadS && std::abs(rz) <= kMaxGyroRadS &&
                       std::abs(dx) <= kMaxAccMS2 && std::abs(dy) <= kMaxAccMS2 && std::abs(dz) <= kMaxAccMS2) {
                     vImuMeas.push_back(ORB_SLAM3::IMU::Point(dx, dy, dz, rx, ry, rz, current_time));
                     last_imu_t = t;
                   } else {
                     std::cerr << "skip imu interpolated sample with invalid values in process()" << std::endl;
                   }
                  //  std::cout.setf(std::ios::fixed, std::ios::floatfield);
                  //  std::cout.precision(6);
                  //  cout<<"imu: "<< current_time << " " << dx << " " << dy << " " << dz <<  " " << rx << " " << ry << " " << rz <<endl;
               }
            }
            last_img_t = img.first;
            { // ---- temporary IMU diagnostics ----
              static int dbg_proc = 0;
              if (dbg_proc < 20) {
                std::cerr << "[dbg] proc vImuMeas=" << vImuMeas.size()
                          << " imu_msgs=" << measurement.first.size()
                          << " img_ts=" << img.first << std::endl;
                ++dbg_proc;
              }
            }
            Sophus::SE3f Tcw = SLAM->TrackStereo(img.second.front(), img.second.back(), img.first, vImuMeas);
            Eigen::Vector3f t = Tcw.translation();          Eigen::Quaternionf q = Tcw.unit_quaternion();
            std::cout << std::fixed << std::setprecision(6)
            << "timestamp " << img.first<< " " << t.x() << " " << t.y() << " " << t.z()<< 
            " q " << q.x() << " " << q.y() << " " << q.z() << " " << q.w() << std::endl;

            // --- VIO pose bridge: publish only while tracking is healthy ---
            // Gate on tracking==OK and a minimum settle time after IMU init, so
            // the arm never follows an uninitialized / drifting (pure-visual) pose.
            if (g_pose_socket &&
                SLAM->GetTrackingState() == kTrackingOk &&
                SLAM->GetTimeFromIMUInit() > kMinImuInitAgeSec &&
                std::isfinite(t.x()) && std::isfinite(t.y()) && std::isfinite(t.z()) &&
                std::isfinite(q.x()) && std::isfinite(q.y()) && std::isfinite(q.z()) && std::isfinite(q.w()))
            {
                PublishPose(img.first, t.x(), t.y(), t.z(), q.x(), q.y(), q.z(), q.w());
            }
        }
       }
}


int main(int argc, char *argv[]) {
  if (argc != 3)
  {
        cout << "usage: image_publisher left_image_folder right_image_folder imu_file " << endl;
        return -1;
  }
  std::cout << argv[1] << std::endl;
  std::cout << argv[2] << std::endl;
  cv::FileStorage fsSettings(argv[2], cv::FileStorage::READ);
  if (!fsSettings.isOpened()) {
    std::cerr << "Failed to open settings file: " << argv[2] << std::endl;
    return -1;
  }
  double target_fps = 0.0;
  fsSettings["Camera.fps"] >> target_fps;
  if (!std::isfinite(target_fps) || target_fps <= 0.0) {
    std::cerr << "Invalid Camera.fps in settings file, got: " << target_fps << std::endl;
    return -1;
  }
  const double target_frame_interval = 1.0 / target_fps;
  std::cout << "Target processing fps from settings: " << target_fps << std::endl;

  // bUseViewer=true: Pangolin viewer enabled. Requires a working NVIDIA GLX
  // stack — if you see "Failed to create an OpenGL context", check nvidia-smi
  // for a "Driver/library version mismatch" (usually fixed by a reboot).
  // VIO_HEADLESS=1：不弹 Pangolin 地图窗 + "Current Frame" 跟踪窗（只算 SLAM，
  // 不显示），用于双臂场景——每臂各弹两个 SLAM 窗口叠加看不过来，显示交给合并双目查看器。
  const bool headless = (std::getenv("VIO_HEADLESS") != nullptr);
  ORB_SLAM3::System SLAM_(argv[1], argv[2], ORB_SLAM3::System::IMU_STEREO, !headless);
  SLAM = &SLAM_;

  // Setup ZMQ PUB socket for the VIO pose bridge (scheme A: decoupled).
  // Override the endpoint with VIO_POSE_ZMQ_ENDPOINT (default loopback).
  {
    const char* endpoint = std::getenv("VIO_POSE_ZMQ_ENDPOINT");
    if (!endpoint || endpoint[0] == '\0') endpoint = "tcp://127.0.0.1:5555";
    g_zmq_ctx = zmq_ctx_new();
    g_pose_socket = zmq_socket(g_zmq_ctx, ZMQ_PUB);
    if (!g_pose_socket) {
      std::cerr << "[vio] zmq_socket failed: " << zmq_strerror(zmq_errno()) << std::endl;
    } else if (zmq_bind(g_pose_socket, endpoint) != 0) {
      std::cerr << "[vio] zmq_bind(" << endpoint << ") failed: "
                << zmq_strerror(zmq_errno()) << std::endl;
      zmq_close(g_pose_socket);
      g_pose_socket = nullptr;
    } else {
      std::cout << "[vio] publishing pose on " << endpoint << std::endl;
    }
  }

  // Setup ZMQ PUB socket for the stereo image bridge (scheme A: decoupled).
  // Override the endpoint with VIO_IMG_ZMQ_ENDPOINT (default loopback).
  {
    const char* endpoint = std::getenv("VIO_IMG_ZMQ_ENDPOINT");
    if (!endpoint || endpoint[0] == '\0') endpoint = "tcp://127.0.0.1:5556";
    g_img_socket = zmq_socket(g_zmq_ctx, ZMQ_PUB);
    if (!g_img_socket) {
      std::cerr << "[vio] zmq_socket(img) failed: " << zmq_strerror(zmq_errno()) << std::endl;
    } else if (zmq_bind(g_img_socket, endpoint) != 0) {
      std::cerr << "[vio] zmq_bind(" << endpoint << ") failed: "
                << zmq_strerror(zmq_errno()) << std::endl;
      zmq_close(g_img_socket);
      g_img_socket = nullptr;
    } else {
      std::cout << "[vio] publishing stereo image on " << endpoint << std::endl;
    }
  }

  std::thread measurement_process{process};

  int count_real = 0;
  std::shared_ptr<cyperstereo::uvc::device> cyperstereo_device{nullptr};
  const char* serial_filter = std::getenv("CYPERSTEREO_SERIAL");
  if (!cyperstereo::FindCyperstereoDevices(
          cyperstereo_device, serial_filter ? serial_filter : "")) {
    return 0;
  }
  // Pick the profile from the device's serial number + advertised UVC size
  // (SmartSens duo = 1280x1024@30).  The old code hardcoded 752x480@60 which
  // is the MT9V034; against a 1280x1024 duo that mis-splits every frame.
  const std::string serial_num =
      cyperstereo::uvc::get_serial_number(*cyperstereo_device);
  const cyperstereo::CameraProfile &profile =
      cyperstereo::SelectProfile(serial_num, *cyperstereo_device);
  cyperstereo::FrameInfo frame_info{profile};
  const int num_cameras = profile.num_cameras;
  const bool is_color =
      profile.family == cyperstereo::SensorFamily::kSmartSens;

  cyperstereo::uvc::set_device_mode(
      *cyperstereo_device, profile.frame_width, profile.frame_height,
      static_cast<int>(cyperstereo::Format::YUYV), profile.fps,
      [&frame_info](const void *data, std::function<void()> continuation) {
        cyperstereo::SetStreamData(frame_info, data, continuation);
      });
  cyperstereo::uvc::start_streaming(*cyperstereo_device, 0);

  // SmartSens sensors deliver raw Bayer; convert to BGR before SLAM.
  cyperstereo::IspProcessor isp(cyperstereo::IspMode::kFastBalancedBgr888);
  cv::Mat left_image(profile.frame_height, profile.cam_width, CV_8U);
  cv::Mat right_image(profile.frame_height, profile.cam_width, CV_8U);
  cv::Mat left_color(profile.frame_height, profile.cam_width, CV_8UC3);
  cv::Mat right_color(profile.frame_height, profile.cam_width, CV_8UC3);
  TicToc t_frame;
  double last_imu_timestamp = -1.0;
  double last_image_timestamp = -1.0;
  double last_forwarded_image_timestamp = -1.0;
  while (true) {
    cyperstereo::WaitForStream(frame_info);

    double image_timestamp = 0.0;
    uint32_t hardware_version = 0;
    uint32_t software_version = 0;
    double camera_gain[4]{};
    cyperstereo::IMUStreamData imu_data{};
    cyperstereo::GNSSStreamData gnss_data{};

    {
      std::lock_guard<std::mutex> lock(frame_info.mtx);
      image_timestamp = frame_info.framestream.image_timestamp;
      hardware_version = frame_info.framestream.hardware_version;
      software_version = frame_info.framestream.software_version;
      if (is_color) {
        for (int i = 0; i < num_cameras && i < 4; ++i) {
          camera_gain[i] = frame_info.framestream.camera_gain[i];
        }
      }
      frame_info.framestream.left_image.copyTo(left_image);
      frame_info.framestream.right_image.copyTo(right_image);
      imu_data = frame_info.framestream.imu;
      gnss_data = frame_info.framestream.gnss;
    }

    { // ---- temporary IMU diagnostics ----
      static int dbg_imu = 0;
      if (dbg_imu < 20) {
        std::cerr << "[dbg] imu_count=" << imu_data.imu_count
                  << " img_ts=" << image_timestamp;
        if (imu_data.imu_count > 0) {
          std::cerr << " imu_ts0=" << imu_data.imu_timestamp[0]
                    << " imu_tsN="
                    << imu_data.imu_timestamp[imu_data.imu_count - 1];
        }
        std::cerr << std::endl;
        ++dbg_imu;
      }
    }

    // Use Camera.fps from settings to throttle image forwarding into SLAM.
    const bool should_forward_frame =
        (last_forwarded_image_timestamp < 0.0) ||
        (image_timestamp - last_forwarded_image_timestamp >= target_frame_interval);
    if (should_forward_frame) {
      std::cout << "capture_img_timestamp " << image_timestamp << std::endl;
      // cv::imshow("left", left_image);
      // cv::imshow("right", right_image);
      // cv::waitKey(1);
      if (image_timestamp > 2) {
        if (!std::isfinite(image_timestamp)) {
          std::cerr << "skip image with non-finite timestamp" << std::endl;
        } else if (last_image_timestamp >= 0.0 && image_timestamp <= last_image_timestamp) {
          std::cerr << "skip non-monotonic image timestamp " << std::setprecision(6)
                    << image_timestamp << " <= " << last_image_timestamp << std::endl;
        } else {
          if (is_color) {
            // 2-camera SmartSens: C1 (the mirrored sensor) lands in
            // right_image, so it takes the plane-0 Bayer phase.
            const cyperstereo::BayerConversion mirrored_bayer =
                cyperstereo::SelectBayerConversion(
                    hardware_version, software_version, 0);
            isp.ApplyParallel({
                {left_image, left_color, "cam1", camera_gain[0]},
                {right_image, right_color, "cam2", camera_gain[1],
                 mirrored_bayer},
            });
            if (!headless) { // ---- temporary: show both eyes to verify the stereo pair ----
              cv::Mat side_by_side;
              cv::hconcat(left_color, right_color, side_by_side);
              cv::putText(side_by_side, "L eye (left_color)", cv::Point(10, 30),
                          cv::FONT_HERSHEY_SIMPLEX, 0.8, cv::Scalar(0, 255, 0), 2);
              cv::putText(side_by_side, "R eye (right_color)",
                          cv::Point(left_color.cols + 10, 30),
                          cv::FONT_HERSHEY_SIMPLEX, 0.8, cv::Scalar(0, 255, 0), 2);
              cv::imshow("stereo_pair L|R", side_by_side);
              cv::waitKey(1);
            }
            // s200032 (Cyperstereo S2): SDK "left_image" (C1) = cam1 = physical
            // LEFT eye, "right_image" (C2) = cam0 = physical RIGHT eye (verified:
            // the two unprojected rays only agree vertically when C1 uses cam1
            // intrinsics and C2 uses cam0). Feed left_color as imLeft / right_color
            // as imRight, matching yaml Camera=cam1, Camera2=cam0, Tlr=+0.060.
            InputImage(left_color, right_color, image_timestamp);
            // Forward the same stereo pair to the ROS2 /cam0|1/image_raw bridge.
            PublishStereoImage(image_timestamp, left_color, right_color);
          } else {
            InputImage(right_image, left_image, image_timestamp);
          }
          last_forwarded_image_timestamp = image_timestamp;
          last_image_timestamp = image_timestamp;
          count_real++;
          if (count_real % 10 == 0) {
            double frame_rate = 10 / (t_frame.toc() / 1000);
            t_frame.tic();
            std::cout << "frame_rate " << frame_rate << std::endl;
          }
        }
      }
    }

    //imu data
    for (int i = 0; i < imu_data.imu_count; ++i) {
        double imu_timestamp = imu_data.imu_timestamp[i];
        double gyro_x = imu_data.gyro_x[i];
        double gyro_y = imu_data.gyro_y[i];
        double gyro_z = imu_data.gyro_z[i];
        double acc_x = imu_data.acc_x[i] * g;
        double acc_y = imu_data.acc_y[i] * g;
        double acc_z = imu_data.acc_z[i] * g;
        std::cout.setf(std::ios::fixed, std::ios::floatfield);
        std::cout.precision(6);
        //std::cout << "imu_timestamp " << imu_timestamp << " " << gyro_x << " "<< gyro_y << " "<< gyro_z << " " << acc_x << " "<< acc_y << " " << acc_z << std::endl;
        if (imu_timestamp > 2) {
          if (!std::isfinite(imu_timestamp) || !std::isfinite(gyro_x) || !std::isfinite(gyro_y) ||
              !std::isfinite(gyro_z) || !std::isfinite(acc_x) || !std::isfinite(acc_y) || !std::isfinite(acc_z)) {
            std::cerr << "skip IMU sample with non-finite values" << std::endl;
            continue;
          }
          if (last_imu_timestamp >= 0.0 && imu_timestamp <= last_imu_timestamp) {
            std::cerr << "skip non-monotonic IMU timestamp " << std::setprecision(6)
                      << imu_timestamp << " <= " << last_imu_timestamp << std::endl;
            continue;
          }
          last_imu_timestamp = imu_timestamp;
          InputIMU(imu_timestamp, Eigen::Vector3d(acc_x, acc_y, acc_z), Eigen::Vector3d(gyro_x, gyro_y, gyro_z));
        }
      }

  }
  cyperstereo::uvc::stop_streaming(*cyperstereo_device);

  if (g_pose_socket) { zmq_close(g_pose_socket); g_pose_socket = nullptr; }
  if (g_img_socket) { zmq_close(g_img_socket); g_img_socket = nullptr; }
  if (g_zmq_ctx) { zmq_ctx_term(g_zmq_ctx); g_zmq_ctx = nullptr; }
  
  return 0;
}
