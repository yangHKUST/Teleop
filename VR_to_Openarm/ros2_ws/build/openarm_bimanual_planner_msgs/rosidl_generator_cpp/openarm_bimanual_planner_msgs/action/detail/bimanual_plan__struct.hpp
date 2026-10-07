// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from openarm_bimanual_planner_msgs:action/BimanualPlan.idl
// generated code does not contain a copyright notice

#ifndef OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__STRUCT_HPP_
#define OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'left_ee_pose'
// Member 'right_ee_pose'
#include "geometry_msgs/msg/detail/pose__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Goal __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Goal __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_Goal_
{
  using Type = BimanualPlan_Goal_<ContainerAllocator>;

  explicit BimanualPlan_Goal_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : left_ee_pose(_init),
    right_ee_pose(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->duration = 0.0;
    }
  }

  explicit BimanualPlan_Goal_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : left_ee_pose(_alloc, _init),
    right_ee_pose(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->duration = 0.0;
    }
  }

  // field types and members
  using _left_ee_pose_type =
    geometry_msgs::msg::Pose_<ContainerAllocator>;
  _left_ee_pose_type left_ee_pose;
  using _right_ee_pose_type =
    geometry_msgs::msg::Pose_<ContainerAllocator>;
  _right_ee_pose_type right_ee_pose;
  using _duration_type =
    double;
  _duration_type duration;

  // setters for named parameter idiom
  Type & set__left_ee_pose(
    const geometry_msgs::msg::Pose_<ContainerAllocator> & _arg)
  {
    this->left_ee_pose = _arg;
    return *this;
  }
  Type & set__right_ee_pose(
    const geometry_msgs::msg::Pose_<ContainerAllocator> & _arg)
  {
    this->right_ee_pose = _arg;
    return *this;
  }
  Type & set__duration(
    const double & _arg)
  {
    this->duration = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Goal
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Goal
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_Goal_ & other) const
  {
    if (this->left_ee_pose != other.left_ee_pose) {
      return false;
    }
    if (this->right_ee_pose != other.right_ee_pose) {
      return false;
    }
    if (this->duration != other.duration) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_Goal_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_Goal_

// alias to use template instance with default allocator
using BimanualPlan_Goal =
  openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Result __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Result __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_Result_
{
  using Type = BimanualPlan_Result_<ContainerAllocator>;

  explicit BimanualPlan_Result_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
      this->message = "";
    }
  }

  explicit BimanualPlan_Result_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : message(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
      this->message = "";
    }
  }

  // field types and members
  using _success_type =
    bool;
  _success_type success;
  using _message_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _message_type message;

  // setters for named parameter idiom
  Type & set__success(
    const bool & _arg)
  {
    this->success = _arg;
    return *this;
  }
  Type & set__message(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->message = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Result
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Result
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_Result_ & other) const
  {
    if (this->success != other.success) {
      return false;
    }
    if (this->message != other.message) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_Result_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_Result_

// alias to use template instance with default allocator
using BimanualPlan_Result =
  openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_Feedback_
{
  using Type = BimanualPlan_Feedback_<ContainerAllocator>;

  explicit BimanualPlan_Feedback_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->progress = 0.0f;
    }
  }

  explicit BimanualPlan_Feedback_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->progress = 0.0f;
    }
  }

  // field types and members
  using _progress_type =
    float;
  _progress_type progress;

  // setters for named parameter idiom
  Type & set__progress(
    const float & _arg)
  {
    this->progress = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_Feedback_ & other) const
  {
    if (this->progress != other.progress) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_Feedback_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_Feedback_

// alias to use template instance with default allocator
using BimanualPlan_Feedback =
  openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"
// Member 'goal'
#include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_SendGoal_Request_
{
  using Type = BimanualPlan_SendGoal_Request_<ContainerAllocator>;

  explicit BimanualPlan_SendGoal_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init),
    goal(_init)
  {
    (void)_init;
  }

  explicit BimanualPlan_SendGoal_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init),
    goal(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;
  using _goal_type =
    openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator>;
  _goal_type goal;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }
  Type & set__goal(
    const openarm_bimanual_planner_msgs::action::BimanualPlan_Goal_<ContainerAllocator> & _arg)
  {
    this->goal = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_SendGoal_Request_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    if (this->goal != other.goal) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_SendGoal_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_SendGoal_Request_

// alias to use template instance with default allocator
using BimanualPlan_SendGoal_Request =
  openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_SendGoal_Response_
{
  using Type = BimanualPlan_SendGoal_Response_<ContainerAllocator>;

  explicit BimanualPlan_SendGoal_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
    }
  }

  explicit BimanualPlan_SendGoal_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
    }
  }

  // field types and members
  using _accepted_type =
    bool;
  _accepted_type accepted;
  using _stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _stamp_type stamp;

  // setters for named parameter idiom
  Type & set__accepted(
    const bool & _arg)
  {
    this->accepted = _arg;
    return *this;
  }
  Type & set__stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->stamp = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_SendGoal_Response_ & other) const
  {
    if (this->accepted != other.accepted) {
      return false;
    }
    if (this->stamp != other.stamp) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_SendGoal_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_SendGoal_Response_

// alias to use template instance with default allocator
using BimanualPlan_SendGoal_Response =
  openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace openarm_bimanual_planner_msgs
{

namespace action
{

struct BimanualPlan_SendGoal
{
  using Request = openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Request;
  using Response = openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal_Response;
};

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_GetResult_Request_
{
  using Type = BimanualPlan_GetResult_Request_<ContainerAllocator>;

  explicit BimanualPlan_GetResult_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init)
  {
    (void)_init;
  }

  explicit BimanualPlan_GetResult_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_GetResult_Request_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_GetResult_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_GetResult_Request_

// alias to use template instance with default allocator
using BimanualPlan_GetResult_Request =
  openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


// Include directives for member types
// Member 'result'
// already included above
// #include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_GetResult_Response_
{
  using Type = BimanualPlan_GetResult_Response_<ContainerAllocator>;

  explicit BimanualPlan_GetResult_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : result(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = 0;
    }
  }

  explicit BimanualPlan_GetResult_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : result(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = 0;
    }
  }

  // field types and members
  using _status_type =
    int8_t;
  _status_type status;
  using _result_type =
    openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator>;
  _result_type result;

  // setters for named parameter idiom
  Type & set__status(
    const int8_t & _arg)
  {
    this->status = _arg;
    return *this;
  }
  Type & set__result(
    const openarm_bimanual_planner_msgs::action::BimanualPlan_Result_<ContainerAllocator> & _arg)
  {
    this->result = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_GetResult_Response_ & other) const
  {
    if (this->status != other.status) {
      return false;
    }
    if (this->result != other.result) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_GetResult_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_GetResult_Response_

// alias to use template instance with default allocator
using BimanualPlan_GetResult_Response =
  openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

namespace openarm_bimanual_planner_msgs
{

namespace action
{

struct BimanualPlan_GetResult
{
  using Request = openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Request;
  using Response = openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult_Response;
};

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs


// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"
// Member 'feedback'
// already included above
// #include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage __attribute__((deprecated))
#else
# define DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage __declspec(deprecated)
#endif

namespace openarm_bimanual_planner_msgs
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct BimanualPlan_FeedbackMessage_
{
  using Type = BimanualPlan_FeedbackMessage_<ContainerAllocator>;

  explicit BimanualPlan_FeedbackMessage_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init),
    feedback(_init)
  {
    (void)_init;
  }

  explicit BimanualPlan_FeedbackMessage_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init),
    feedback(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;
  using _feedback_type =
    openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator>;
  _feedback_type feedback;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }
  Type & set__feedback(
    const openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback_<ContainerAllocator> & _arg)
  {
    this->feedback = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator> *;
  using ConstRawPtr =
    const openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage
    std::shared_ptr<openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const BimanualPlan_FeedbackMessage_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    if (this->feedback != other.feedback) {
      return false;
    }
    return true;
  }
  bool operator!=(const BimanualPlan_FeedbackMessage_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct BimanualPlan_FeedbackMessage_

// alias to use template instance with default allocator
using BimanualPlan_FeedbackMessage =
  openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

#include "action_msgs/srv/cancel_goal.hpp"
#include "action_msgs/msg/goal_info.hpp"
#include "action_msgs/msg/goal_status_array.hpp"

namespace openarm_bimanual_planner_msgs
{

namespace action
{

struct BimanualPlan
{
  /// The goal message defined in the action definition.
  using Goal = openarm_bimanual_planner_msgs::action::BimanualPlan_Goal;
  /// The result message defined in the action definition.
  using Result = openarm_bimanual_planner_msgs::action::BimanualPlan_Result;
  /// The feedback message defined in the action definition.
  using Feedback = openarm_bimanual_planner_msgs::action::BimanualPlan_Feedback;

  struct Impl
  {
    /// The send_goal service using a wrapped version of the goal message as a request.
    using SendGoalService = openarm_bimanual_planner_msgs::action::BimanualPlan_SendGoal;
    /// The get_result service using a wrapped version of the result message as a response.
    using GetResultService = openarm_bimanual_planner_msgs::action::BimanualPlan_GetResult;
    /// The feedback message with generic fields which wraps the feedback message.
    using FeedbackMessage = openarm_bimanual_planner_msgs::action::BimanualPlan_FeedbackMessage;

    /// The generic service to cancel a goal.
    using CancelGoalService = action_msgs::srv::CancelGoal;
    /// The generic message for the status of a goal.
    using GoalStatusMessage = action_msgs::msg::GoalStatusArray;
  };
};

typedef struct BimanualPlan BimanualPlan;

}  // namespace action

}  // namespace openarm_bimanual_planner_msgs

#endif  // OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__STRUCT_HPP_
