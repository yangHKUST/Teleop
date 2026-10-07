// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from openarm_bimanual_planner_msgs:action/BimanualPlan.idl
// generated code does not contain a copyright notice

#ifndef OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__STRUCT_H_
#define OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'left_ee_pose'
// Member 'right_ee_pose'
#include "geometry_msgs/msg/detail/pose__struct.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_Goal
{
  geometry_msgs__msg__Pose left_ee_pose;
  geometry_msgs__msg__Pose right_ee_pose;
  /// desired duration; 0 = planner default (4.0 s)
  double duration;
} openarm_bimanual_planner_msgs__action__BimanualPlan_Goal;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_Goal.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'message'
#include "rosidl_runtime_c/string.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_Result
{
  bool success;
  rosidl_runtime_c__String message;
} openarm_bimanual_planner_msgs__action__BimanualPlan_Result;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_Result.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_Result * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence;


// Constants defined in the message

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback
{
  /// 0.0 .. 1.0
  float progress;
} openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__struct.h"
// Member 'goal'
#include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request
{
  unique_identifier_msgs__msg__UUID goal_id;
  openarm_bimanual_planner_msgs__action__BimanualPlan_Goal goal;
} openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response
{
  bool accepted;
  builtin_interfaces__msg__Time stamp;
} openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request
{
  unique_identifier_msgs__msg__UUID goal_id;
} openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'result'
// already included above
// #include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response
{
  int8_t status;
  openarm_bimanual_planner_msgs__action__BimanualPlan_Result result;
} openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.h"
// Member 'feedback'
// already included above
// #include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.h"

/// Struct defined in action/BimanualPlan in the package openarm_bimanual_planner_msgs.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage
{
  unique_identifier_msgs__msg__UUID goal_id;
  openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback feedback;
} openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage;

// Struct for a sequence of openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage.
typedef struct openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence
{
  openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__STRUCT_H_
