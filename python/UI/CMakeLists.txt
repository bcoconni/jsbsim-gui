set(JSBSIM_UI_PACKAGE_DIR ${CMAKE_BINARY_DIR}/python/jsbsim/UI)
file(MAKE_DIRECTORY ${JSBSIM_UI_PACKAGE_DIR})
set(JSBSIM_UI_TEST_PACKAGE_DIR ${CMAKE_BINARY_DIR}/tests/jsbsim/UI)
file(MAKE_DIRECTORY ${JSBSIM_UI_TEST_PACKAGE_DIR})

set(SOURCES __init__.py
            __main__.py
            app.py
            controller.py
            hierarchical_tree.py
            plots_view.py
            run.py
            source_editor.py
            textview.py)

foreach(_FILE ${SOURCES})
    configure_file(${CMAKE_CURRENT_SOURCE_DIR}/${_FILE} ${JSBSIM_UI_PACKAGE_DIR} COPYONLY)
    configure_file(${CMAKE_CURRENT_SOURCE_DIR}/${_FILE} ${JSBSIM_UI_TEST_PACKAGE_DIR} COPYONLY)
endforeach()
