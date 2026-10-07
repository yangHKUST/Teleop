// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from openarm_bimanual_planner_msgs:action/BimanualPlan.idl
// generated code does not contain a copyright notice

#ifndef OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__TRAITS_HPP_
#define OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'left_ee_pose'
// Member 'right_ee_pose'
#include "geometry_msgs/msg/detail/pose__traits.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_Goal & msg,
  std::ostream & out)
{
  out << "{";
  // member: left_ee_pose
  {
    out << "left_ee_pose: ";
    to_flow_style_yaml(msg.left_ee_pose, out);
    out << ", ";
  }

  // member: right_ee_pose
  {
    out << "right_ee_pose: ";
    to_flow_style_yaml(msg.right_ee_pose, out);
    out << ", ";
  }

  // member: duration
  {
    out << "duration: ";
    rosidl_generator_traits::value_to_yaml(msg.duration, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_Goal & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: left_ee_pose
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "left_ee_pose:\n";
    to_block_style_yaml(msg.left_ee_pose, out, indentation + 2);
  }

  // member: right_ee_pose
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "right_ee_pose:\n";
    to_block_style_yaml(msg.right_ee_pose, out, indentation + 2);
  }

  // member: duration
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "duration: ";
    rosidl_generator_traits::value_to_yaml(msg.duration, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_Goal & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_Goal & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_Goal & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_Goal";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_Goal";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>
  : std::integral_constant<bool, has_fixed_size<geometry_msgs::msg::Pose>::value> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>
  : std::integral_constant<bool, has_bounded_size<geometry_msgs::msg::Pose>::value> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_Result & msg,
  std::ostream & out)
{
  out << "{";
  // member: success
  {
    out << "success: ";
    rosidl_generator_traits::value_to_yaml(msg.success, out);
    out << ", ";
  }

  // member: message
  {
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_Result & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: success
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "success: ";
    rosidl_generator_traits::value_to_yaml(msg.success, out);
    out << "\n";
  }

  // member: message
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_Result & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_Result & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_Result & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_Result";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_Result";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_Feedback & msg,
  std::ostream & out)
{
  out << "{";
  // member: progress
  {
    out << "progress: ";
    rosidl_generator_traits::value_to_yaml(msg.progress, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_Feedback & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: progress
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "progress: ";
    rosidl_generator_traits::value_to_yaml(msg.progress, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_Feedback & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_Feedback";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__traits.hpp"
// Member 'goal'
#include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__traits.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_SendGoal_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: goal_id
  {
    out << "goal_id: ";
    to_flow_style_yaml(msg.goal_id, out);
    out << ", ";
  }

  // member: goal
  {
    out << "goal: ";
    to_flow_style_yaml(msg.goal, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_SendGoal_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: goal_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "goal_id:\n";
    to_block_style_yaml(msg.goal_id, out, indentation + 2);
  }

  // member: goal
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "goal:\n";
    to_block_style_yaml(msg.goal, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_SendGoal_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_SendGoal_Request";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>
  : std::integral_constant<bool, has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>::value && has_fixed_size<unique_identifier_msgs::msg::UUID>::value> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>
  : std::integral_constant<bool, has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>::value && has_bounded_size<unique_identifier_msgs::msg::UUID>::value> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__traits.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_SendGoal_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: accepted
  {
    out << "accepted: ";
    rosidl_generator_traits::value_to_yaml(msg.accepted, out);
    out << ", ";
  }

  // member: stamp
  {
    out << "stamp: ";
    to_flow_style_yaml(msg.stamp, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_SendGoal_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: accepted
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "accepted: ";
    rosidl_generator_traits::value_to_yaml(msg.accepted, out);
    out << "\n";
  }

  // member: stamp
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "stamp:\n";
    to_block_style_yaml(msg.stamp, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_SendGoal_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_SendGoal_Response";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>
  : std::integral_constant<bool, has_fixed_size<builtin_interfaces::msg::Time>::value> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>
  : std::integral_constant<bool, has_bounded_size<builtin_interfaces::msg::Time>::value> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_SendGoal";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal>
  : std::integral_constant<
    bool,
    has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>::value &&
    has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>::value
  >
{
};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal>
  : std::integral_constant<
    bool,
    has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>::value &&
    has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>::value
  >
{
};

template<>
struct is_service<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal>
  : std::true_type
{
};

template<>
struct is_service_request<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>
  : std::true_type
{
};

template<>
struct is_service_response<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__traits.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_GetResult_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: goal_id
  {
    out << "goal_id: ";
    to_flow_style_yaml(msg.goal_id, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_GetResult_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: goal_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "goal_id:\n";
    to_block_style_yaml(msg.goal_id, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_GetResult_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_GetResult_Request";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>
  : std::integral_constant<bool, has_fixed_size<unique_identifier_msgs::msg::UUID>::value> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>
  : std::integral_constant<bool, has_bounded_size<unique_identifier_msgs::msg::UUID>::value> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'result'
// already included above
// #include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__traits.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_GetResult_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: status
  {
    out << "status: ";
    rosidl_generator_traits::value_to_yaml(msg.status, out);
    out << ", ";
  }

  // member: result
  {
    out << "result: ";
    to_flow_style_yaml(msg.result, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_GetResult_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: status
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "status: ";
    rosidl_generator_traits::value_to_yaml(msg.status, out);
    out << "\n";
  }

  // member: result
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "result:\n";
    to_block_style_yaml(msg.result, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_GetResult_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_GetResult_Response";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>
  : std::integral_constant<bool, has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>::value> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>
  : std::integral_constant<bool, has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>::value> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_GetResult";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult>
  : std::integral_constant<
    bool,
    has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>::value &&
    has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>::value
  >
{
};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult>
  : std::integral_constant<
    bool,
    has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>::value &&
    has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>::value
  >
{
};

template<>
struct is_service<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult>
  : std::true_type
{
};

template<>
struct is_service_request<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>
  : std::true_type
{
};

template<>
struct is_service_response<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__traits.hpp"
// Member 'feedback'
// already included above
// #include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__traits.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

inline void to_flow_style_yaml(
  const BimanualPlan_FeedbackMessage & msg,
  std::ostream & out)
{
  out << "{";
  // member: goal_id
  {
    out << "goal_id: ";
    to_flow_style_yaml(msg.goal_id, out);
    out << ", ";
  }

  // member: feedback
  {
    out << "feedback: ";
    to_flow_style_yaml(msg.feedback, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const BimanualPlan_FeedbackMessage & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: goal_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "goal_id:\n";
    to_block_style_yaml(msg.goal_id, out, indentation + 2);
  }

  // member: feedback
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "feedback:\n";
    to_block_style_yaml(msg.feedback, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const BimanualPlan_FeedbackMessage & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace rosidl_generator_traits
{

[[deprecated("use openarm_bimanual_planner_msgs::action::to_block_style_yaml() instead")]]
inline void to_yaml(
  const openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage & msg,
  std::ostream & out, size_t indentation = 0)
{
  openarm_bimanual_planner_msgs::action::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use openarm_bimanual_planner_msgs::action::to_yaml() instead")]]
inline std::string to_yaml(const openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage & msg)
{
  return openarm_bimanual_planner_msgs::action::to_yaml(msg);
}

template<>
inline const char * data_type<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage>()
{
  return "openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage";
}

template<>
inline const char * name<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage>()
{
  return "openarm_bimanual_planner_msgs/action/BimanualPlan_FeedbackMessage";
}

template<>
struct has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage>
  : std::integral_constant<bool, has_fixed_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>::value && has_fixed_size<unique_identifier_msgs::msg::UUID>::value> {};

template<>
struct has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage>
  : std::integral_constant<bool, has_bounded_size<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>::value && has_bounded_size<unique_identifier_msgs::msg::UUID>::value> {};

template<>
struct is_message<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage>
  : std::true_type {};

}  // namespace rosidl_generator_traits


namespace rosidl_generator_traits
{

template<>
struct is_action<openarm_bimanual_planner_msgs::action::BimanualPlan>
  : std::true_type
{
};

template<>
struct is_action_goal<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>
  : std::true_type
{
};

template<>
struct is_action_result<openarm_bimanual_planner_msgs::action::BimanualPlan_Result>
  : std::true_type
{
};

template<>
struct is_action_feedback<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits


#endif  // OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__TRAITS_HPP_
