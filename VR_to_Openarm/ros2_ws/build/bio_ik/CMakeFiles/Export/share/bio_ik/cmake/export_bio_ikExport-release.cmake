#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "bio_ik::bio_ik" for configuration "Release"
set_property(TARGET bio_ik::bio_ik APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(bio_ik::bio_ik PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libbio_ik.so"
  IMPORTED_SONAME_RELEASE "libbio_ik.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS bio_ik::bio_ik )
list(APPEND _IMPORT_CHECK_FILES_FOR_bio_ik::bio_ik "${_IMPORT_PREFIX}/lib/libbio_ik.so" )

# Import target "bio_ik::bio_ik_plugin" for configuration "Release"
set_property(TARGET bio_ik::bio_ik_plugin APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(bio_ik::bio_ik_plugin PROPERTIES
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "bio_ik::bio_ik"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libbio_ik_plugin.so"
  IMPORTED_SONAME_RELEASE "libbio_ik_plugin.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS bio_ik::bio_ik_plugin )
list(APPEND _IMPORT_CHECK_FILES_FOR_bio_ik::bio_ik_plugin "${_IMPORT_PREFIX}/lib/libbio_ik_plugin.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
