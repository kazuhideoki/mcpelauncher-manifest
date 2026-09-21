# Apply the confirmed client fix without modifying the pinned upstream checkout.
# This is paired with the game-window fork's native Joy-Con gamepad default.
set(joycon_client_source "${CMAKE_SOURCE_DIR}/mcpelauncher-client/src/window_callbacks.cpp")
file(READ "${joycon_client_source}" joycon_client_text)
set(joycon_old_source "ev.source = AINPUT_SOURCE_GAMEPAD;")
string(REGEX MATCHALL "ev\\.source = AINPUT_SOURCE_GAMEPAD" joycon_matches "${joycon_client_text}")
list(LENGTH joycon_matches joycon_match_count)
if(NOT joycon_match_count EQUAL 1)
    message(FATAL_ERROR "Joy-Con client fix expects exactly one GameActivity gamepad motion source; review the pinned client")
endif()
string(REPLACE "${joycon_old_source}" "ev.source = AINPUT_SOURCE_JOYSTICK;" joycon_client_text "${joycon_client_text}")
file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/joycon-generated")
set(joycon_fixed_source "${CMAKE_BINARY_DIR}/joycon-generated/window_callbacks.cpp")
# Avoid changing timestamps on repeated setup when the source is identical.
file(WRITE "${CMAKE_BINARY_DIR}/joycon-generated/window_callbacks.cpp.in" "${joycon_client_text}")
configure_file("${CMAKE_BINARY_DIR}/joycon-generated/window_callbacks.cpp.in" "${joycon_fixed_source}" COPYONLY)
set_source_files_properties("${joycon_client_source}"
    DIRECTORY "${CMAKE_SOURCE_DIR}/mcpelauncher-client" PROPERTIES HEADER_FILE_ONLY TRUE)
target_sources(mcpelauncher-client PRIVATE "${joycon_fixed_source}")
target_include_directories(mcpelauncher-client PRIVATE "${CMAKE_SOURCE_DIR}/mcpelauncher-client/src")
