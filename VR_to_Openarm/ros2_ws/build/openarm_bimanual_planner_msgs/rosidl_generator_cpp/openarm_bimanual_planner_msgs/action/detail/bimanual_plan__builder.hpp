// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from openarm_bimanual_planner_msgs:action/BimanualPlan.idl
// generated code does not contain a copyright notice

#ifndef OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__BUILDER_HPP_
#define OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_Goal_duration
{
public:
  explicit Init_BimanualPlan_Goal_duration(::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal & msg)
  : msg_(msg)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal duration(::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal::_duration_type arg)
  {
    msg_.duration = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal msg_;
};

class Init_BimanualPlan_Goal_right_ee_pose
{
public:
  explicit Init_BimanualPlan_Goal_right_ee_pose(::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal & msg)
  : msg_(msg)
  {}
  Init_BimanualPlan_Goal_duration right_ee_pose(::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal::_right_ee_pose_type arg)
  {
    msg_.right_ee_pose = std::move(arg);
    return Init_BimanualPlan_Goal_duration(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal msg_;
};

class Init_BimanualPlan_Goal_left_ee_pose
{
public:
  Init_BimanualPlan_Goal_left_ee_pose()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_BimanualPlan_Goal_right_ee_pose left_ee_pose(::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal::_left_ee_pose_type arg)
  {
    msg_.left_ee_pose = std::move(arg);
    return Init_BimanualPlan_Goal_right_ee_pose(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_Goal>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_Goal_left_ee_pose();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_Result_message
{
public:
  explicit Init_BimanualPlan_Result_message(::openarm_bimanual_planner_msgs::action::BimanualPlan_Result & msg)
  : msg_(msg)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Result message(::openarm_bimanual_planner_msgs::action::BimanualPlan_Result::_message_type arg)
  {
    msg_.message = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Result msg_;
};

class Init_BimanualPlan_Result_success
{
public:
  Init_BimanualPlan_Result_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_BimanualPlan_Result_message success(::openarm_bimanual_planner_msgs::action::BimanualPlan_Result::_success_type arg)
  {
    msg_.success = std::move(arg);
    return Init_BimanualPlan_Result_message(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Result msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_Result>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_Result_success();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_Feedback_progress
{
public:
  Init_BimanualPlan_Feedback_progress()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback progress(::openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback::_progress_type arg)
  {
    msg_.progress = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_Feedback_progress();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_SendGoal_Request_goal
{
public:
  explicit Init_BimanualPlan_SendGoal_Request_goal(::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request & msg)
  : msg_(msg)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request goal(::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request::_goal_type arg)
  {
    msg_.goal = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request msg_;
};

class Init_BimanualPlan_SendGoal_Request_goal_id
{
public:
  Init_BimanualPlan_SendGoal_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_BimanualPlan_SendGoal_Request_goal goal_id(::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_BimanualPlan_SendGoal_Request_goal(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_SendGoal_Request_goal_id();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_SendGoal_Response_stamp
{
public:
  explicit Init_BimanualPlan_SendGoal_Response_stamp(::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response & msg)
  : msg_(msg)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response stamp(::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response::_stamp_type arg)
  {
    msg_.stamp = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response msg_;
};

class Init_BimanualPlan_SendGoal_Response_accepted
{
public:
  Init_BimanualPlan_SendGoal_Response_accepted()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_BimanualPlan_SendGoal_Response_stamp accepted(::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response::_accepted_type arg)
  {
    msg_.accepted = std::move(arg);
    return Init_BimanualPlan_SendGoal_Response_stamp(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_SendGoal_Response_accepted();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_GetResult_Request_goal_id
{
public:
  Init_BimanualPlan_GetResult_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request goal_id(::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_GetResult_Request_goal_id();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_GetResult_Response_result
{
public:
  explicit Init_BimanualPlan_GetResult_Response_result(::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response & msg)
  : msg_(msg)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response result(::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response::_result_type arg)
  {
    msg_.result = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response msg_;
};

class Init_BimanualPlan_GetResult_Response_status
{
public:
  Init_BimanualPlan_GetResult_Response_status()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_BimanualPlan_GetResult_Response_result status(::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response::_status_type arg)
  {
    msg_.status = std::move(arg);
    return Init_BimanualPlan_GetResult_Response_result(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_GetResult_Response_status();
}

}  // namespace openarm_bimanual_planner_msgs


namespace openarm_bimanual_planner_msgs
{

namespace action
{

namespace builder
{

class Init_BimanualPlan_FeedbackMessage_feedback
{
public:
  explicit Init_BimanualPlan_FeedbackMessage_feedback(::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage & msg)
  : msg_(msg)
  {}
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage feedback(::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage::_feedback_type arg)
  {
    msg_.feedback = std::move(arg);
    return std::move(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage msg_;
};

class Init_BimanualPlan_FeedbackMessage_goal_id
{
public:
  Init_BimanualPlan_FeedbackMessage_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_BimanualPlan_FeedbackMessage_feedback goal_id(::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_BimanualPlan_FeedbackMessage_feedback(msg_);
  }

private:
  ::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage>()
{
  return openarm_bimanual_planner_msgs::action::builder::Init_BimanualPlan_FeedbackMessage_goal_id();
}

}  // namespace openarm_bimanual_planner_msgs

#endif  // OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__BUILDER_HPP_
