# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_openarm_acm_tool_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED openarm_acm_tool_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(openarm_acm_tool_FOUND FALSE)
  elseif(NOT openarm_acm_tool_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(openarm_acm_tool_FOUND FALSE)
  endif()
  return()
endif()
set(_openarm_acm_tool_CONFIG_INCLUDED TRUE)

# output package information
if(NOT openarm_acm_tool_FIND_QUIETLY)
  message(STATUS "Found openarm_acm_tool: 0.0.0 (${openarm_acm_tool_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'openarm_acm_tool' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${openarm_acm_tool_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(openarm_acm_tool_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${openarm_acm_tool_DIR}/${_extra}")
endforeach()
