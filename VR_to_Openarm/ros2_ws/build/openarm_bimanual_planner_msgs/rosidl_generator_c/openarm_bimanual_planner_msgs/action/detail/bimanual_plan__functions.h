// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from openarm_bimanual_planner_msgs:action/BimanualPlan.idl
// generated code does not contain a copyright notice

#ifndef OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__FUNCTIONS_H_
#define OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "openarm_bimanual_planner_msgs/msg/rosidl_generator_c__visibility_control.h"

#include "openarm_bimanual_planner_msgs/action/detail/bimanual_plan__struct.h"

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__init(openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal *
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_Goal * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_Goal__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__init(openarm_bimanual_planner_msgs__action__BimanualPlan_Result * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_Result * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_Result *
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_Result * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_Result * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_Result * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_Result * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_Result * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_Result__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__init(openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback *
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_Feedback__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__init(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request *
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Request__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__init(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response *
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_SendGoal_Response__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__init(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request *
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Request__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__init(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response *
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_GetResult_Response__Sequence * output);

/// Initialize action/BimanualPlan message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage
 * )) before or use
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__init(openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * msg);

/// Finalize action/BimanualPlan message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * msg);

/// Create action/BimanualPlan message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage *
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__create();

/// Destroy action/BimanualPlan message.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * msg);

/// Check for action/BimanualPlan message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * rhs);

/// Copy a action/BimanualPlan message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage * output);

/// Initialize array of action/BimanualPlan messages.
/**
 * It allocates the memory for the number of elements and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__init(openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * array, size_t size);

/// Finalize array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__fini(openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * array);

/// Create array of action/BimanualPlan messages.
/**
 * It allocates the memory for the array and calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence *
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__create(size_t size);

/// Destroy array of action/BimanualPlan messages.
/**
 * It calls
 * openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
void
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__destroy(openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * array);

/// Check for action/BimanualPlan message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__are_equal(const openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * lhs, const openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * rhs);

/// Copy an array of action/BimanualPlan messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_openarm_bimanual_planner_msgs
bool
openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence__copy(
  const openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * input,
  openarm_bimanual_planner_msgs__action__BimanualPlan_FeedbackMessage__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // OPENARM_BIMANUAL_PLANNER_MSGS__ACTION__DETAIL__BIMANUAL_PLAN__FUNCTIONS_H_
