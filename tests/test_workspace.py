# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License, version 3 or later.

import os
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from jsbsim_gui.app import App
from jsbsim_gui.controller import Controller
from jsbsim_gui.csv_tree import CsvData
from jsbsim_gui.edit_actions import EditAction
from jsbsim_gui.plotinfo_list import PlotInfoList
from jsbsim_gui.project_files import ProjectFiles
from jsbsim_gui.source_editor import SourceEditor


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.withdraw()
        filename = os.path.join(self.app.root_dir, "aircraft", "c172p", "c172p.xml")
        self.assertTrue(self.app.open_file(filename, "c172p", Controller.load_aircraft))
        self.editor = self.app.editor
        assert isinstance(self.editor, SourceEditor)
        self.files = self.app.project_files
        assert isinstance(self.files, ProjectFiles)
        self.app.update()

    def tearDown(self):
        self.app._controller.close()
        self.app.destroy()

    def test_application_owns_notebook_and_sidebar_widgets(self):
        self.assertIs(self.editor.master, self.app.notebook)
        self.assertIs(self.app.plots_view.master, self.app.notebook)
        self.assertIs(self.files.master, self.app.left_frame)
        self.assertIs(self.files._fileview.master, self.files)
        self.assertIs(self.app.property_view.master, self.app.left_frame)
        self.assertIs(self.app.csv_view.master, self.app.left_frame)
        controls = self.app.simulation_controls
        self.assertIs(controls.master, self.app.left_frame)
        self.assertIs(controls.init_button.master, controls)
        self.assertIs(controls.step_button.master, controls)
        self.assertIs(controls.run_pause_button.master, controls)
        self.assertIs(controls.trim_button.master, controls)
        for name in (
            "notebook",
            "run_view",
            "fileview",
            "property_view",
            "_file_states",
            "save_file",
            "save_all",
            "has_modified_files",
            "_find_window",
            "_open_find_window",
            "find_property",
        ):
            self.assertFalse(hasattr(self.editor, name))
        for name in ("csv_tree", "plots_view", "property_view"):
            self.assertFalse(hasattr(controls, name))

    def test_tabs_preserve_editor_and_navigation_selects_editor(self):
        editor = self.editor
        item = self.files._fileview.get_id_from_path(self.files.current_file.filepath)
        self.files._fileview.selection_set([item])
        self.app.update()
        self.app.notebook.select(self.app.plots_view)
        with patch.object(self.files._fileview, "identify_row", return_value=item):
            self.files._on_file_click(SimpleNamespace(y=0))
        self.assertEqual(self.app.notebook.select(), str(editor))

        self.app.notebook.select(self.app.plots_view)
        self.app._on_file_link_click(self.files.current_file.filepath, 1)
        self.assertEqual(self.app.notebook.select(), str(editor))

    def test_csv_loading_keeps_current_tab(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "test.csv")
            with open(path, "w", encoding="utf-8") as file:
                file.write("time,value\n0,1\n1,2\n")
            self.app.load_csv(path)
            self.assertTrue(self.app.csv_tree.has_loaded_files())
            self.assertEqual(self.app.notebook.select(), str(self.editor))

    def test_simulation_continues_on_editor_tab_and_save_does_not_reload(self):
        run = self.app.simulation_controls
        run.run_ic()
        run.run()
        update_id = run.update_id
        self.files.current_file.is_modified = True

        def save_file(root_dir):
            self.files.current_file.is_modified = False
            return True

        with patch.object(self.files.current_file, "write", side_effect=save_file):
            with patch.object(self.app._controller, "reload") as reload_model:
                self.assertTrue(self.files.save_file())
                reload_model.assert_not_called()
        self.assertEqual(run.update_id, update_id)
        self.assertEqual(self.app.notebook.select(), str(self.editor))
        self.assertEqual(
            self.app._statusbar.cget("text"),
            "Files saved. Reload the model to apply changes.",
        )
        time.sleep(0.25)
        self.app.update()
        self.assertGreater(self.app._controller.fdm.get_sim_time(), 0.0)
        run.pause()

    def test_drag_sources_feed_the_shared_plot_view(self):
        property_tree = self.app.property_view.widget
        tree = property_tree.tree
        item = tree.get_children()[0]
        while tree.get_children(item):
            item = tree.get_children(item)[0]
        tree.selection_set([item])
        preview = self.app.dnd_properties.create_source_widget(self.app)
        self.assertIsNotNone(preview)
        with patch.object(self.app.plots_view, "add_data") as add_data:
            self.app.dnd_properties.drop_on_target(None)
            self.assertTrue(add_data.call_args.args[0])
        preview.destroy()

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "test.csv")
            with open(path, "w", encoding="utf-8") as file:
                file.write("time,value\n0,1\n1,2\n")
            self.app.load_csv(path)
            tree = self.app.csv_tree.tree
            item = tree.get_children(tree.get_children()[0])[0]
            tree.selection_set([item])
            preview = self.app.dnd_csv_columns.create_source_widget(self.app)
            self.assertIsNotNone(preview)
            with patch.object(self.app.plots_view, "add_data") as add_data:
                self.app.dnd_csv_columns.drop_on_target(None)
                self.assertEqual(add_data.call_args.args[0][0].name, "value")
            preview.destroy()

    def test_reload_keeps_csv_curves_and_replaces_property_tree(self):
        run = self.app.simulation_controls
        run.run_ic()
        run.step()
        plots = PlotInfoList(self.app._controller)
        plots.add_properties([self.app._controller.get_property_list()[0]])
        plots.add_csv_columns(
            [CsvData("test.csv", "value", np.array([0.0, 1.0]), np.array([1.0, 2.0]))]
        )
        self.app.plots_view.plots = [plots]
        self.app.plots_view.initialize_canvas()
        old_tree = self.app.property_view.widget
        old_fdm = self.app._controller.fdm

        self.app.reload_model()
        self.app.update()

        self.assertIsNot(old_fdm, self.app._controller.fdm)
        self.assertIsNot(old_tree, self.app.property_view.widget)
        self.assertEqual(len(self.app.plots_view.plots), 1)
        self.assertEqual(len(self.app.plots_view.plots[0]), 1)
        self.assertEqual(self.app.plots_view.plots[0][0].name, "value")
        self.assertEqual(str(run.init_button["state"]), "normal")
        self.assertEqual(str(run.step_button["state"]), "disabled")
        self.assertFalse(self.files.has_modified_files())
        self.assertIs(self.app.dnd_properties._source_tree, self.app.property_tree)

    def test_file_selection_and_editor_navigation_are_coordinated_by_app(self):
        file_states = self.files.get_file_states()
        paths = list(file_states)
        other = next(path for path in paths if path != self.files.current_file.filepath)
        self.app.notebook.select(self.app.plots_view)
        self.app._select_source_file(file_states[other])
        self.assertEqual(self.files.current_file.filepath, other)
        self.assertEqual(self.app.notebook.select(), str(self.editor))
        file_state = self.files.get_file_state(paths[0])
        assert file_state is not None
        self.editor.move_to(file_state, True, 0, 1)
        item = self.files._fileview.get_id_from_path(paths[0])
        self.assertEqual(self.files._fileview.selection(), (item,))

    def test_switching_files_preserves_unsaved_editor_content(self):
        original = self.files.current_file
        file_states = self.files.get_file_states()
        other_path = next(path for path in file_states if path != original.filepath)
        editor = self.editor._codeview.widget
        editor._text.insert("end-1c", "\n<!-- changed -->")
        self.app.update()
        self.assertTrue(original.is_modified)
        self.app._select_source_file(file_states[other_path])
        self.assertIn("<!-- changed -->", original.content)
        self.app._select_source_file(original)
        self.assertIn("<!-- changed -->", self.editor.get_content())
        self.assertIs(self.files.current_file, original)

    def test_save_all_navigates_to_invalid_file(self):
        first = self.files.current_file
        file_states = self.files.get_file_states()
        other_path = next(path for path in file_states if path != first.filepath)
        self.files.mark_current_modified(True)
        self.app._select_source_file(file_states[other_path])
        second = self.files.current_file
        self.files.mark_current_modified(True)
        self.app.notebook.select(self.app.plots_view)
        with patch.object(first, "validate_xml", return_value=(2, 1)):
            self.assertFalse(self.files.save_all())
        self.assertIs(self.files.current_file, first)
        self.assertTrue(first.is_modified)
        self.assertTrue(second.is_modified)
        self.assertEqual(self.app.notebook.select(), str(self.editor))
        item = self.files._fileview.get_id_from_path(first.filepath)
        self.assertEqual(self.files._fileview.selection(), (item,))

    def test_search_receives_project_file_states(self):
        with patch("jsbsim_gui.app.FindWindow") as find_window:
            self.app._open_find_window()
        self.assertIs(find_window.call_args.args[2], self.files.get_file_states())
        self.assertEqual(find_window.call_args.args[3], self.editor.select_text)
        with patch.object(self.editor, "move_to") as move_to:
            find_window.call_args.args[4](self.files.current_file, 2, 3)
        move_to.assert_called_once_with(self.files.current_file, True, 2, 3)

    def test_file_modified_notifications_update_the_app_file_tree(self):
        state = self.files.current_file
        item = self.files._fileview.get_id_from_path(state.filepath)
        self.editor._editor._text.insert("end-1c", "\n<!-- changed -->")
        self.app.update()
        self.assertTrue(state.is_modified)
        self.assertIn("modified", self.files._fileview.item(item, "tags"))

        def save_file(root_dir):
            state.is_modified = False
            return True

        with patch.object(state, "write", side_effect=save_file):
            self.assertTrue(self.files.save_file())
        self.assertNotIn("modified", self.files._fileview.item(item, "tags"))

    def test_property_search_is_managed_by_app(self):
        tree = self.app.property_tree.tree
        item = tree.get_children()[0]
        tree.selection_set([item])
        names = self.app.property_tree.get_selected_property_names(False)
        with patch.object(self.app, "_open_find_window") as open_find_window:
            self.app._find_property(None)
        open_find_window.return_value.find_property.assert_called_once_with(names[0])

    def test_find_action_opens_search_from_either_tab(self):
        with patch.object(self.app, "_open_find_window") as open_find_window:
            for tab in (self.editor, self.app.plots_view):
                self.app.notebook.select(tab)
                self.app.edit_action(EditAction.FIND)
            self.assertEqual(open_find_window.call_count, 2)

    def test_find_window_is_reused_and_reopened_after_close(self):
        window = self.app._open_find_window()
        self.assertIs(window.master, self.app)
        self.assertIs(self.app._open_find_window(), window)
        window.destroy()
        replacement = self.app._open_find_window()
        self.assertIsNot(replacement, window)
        self.assertTrue(replacement.winfo_exists())

    def test_find_window_closes_after_reload_and_workspace_replacement(self):
        window = self.app._open_find_window()
        with patch.object(self.app._controller, "reload", return_value=False):
            with patch("jsbsim_gui.app.showerror"):
                self.app.reload_model()
        self.assertTrue(window.winfo_exists())
        self.app.reload_model()
        self.assertFalse(window.winfo_exists())
        self.assertIsNone(self.app._find_window)

        window = self.app._open_find_window()
        self.app.edit()
        self.assertFalse(window.winfo_exists())
        self.assertIsNone(self.app._find_window)

    def test_reload_requires_saved_files_and_confirms_running(self):
        run = self.app.simulation_controls
        self.files.current_file.is_modified = True
        with patch("jsbsim_gui.app.showerror") as error:
            with patch.object(self.app._controller, "reload") as reload_model:
                self.app.reload_model()
                error.assert_called_once()
                reload_model.assert_not_called()
        self.files.current_file.is_modified = False
        run.run_ic()
        run.run()
        with patch("jsbsim_gui.app.askyesno", return_value=False):
            with patch.object(self.app._controller, "reload") as reload_model:
                self.app.reload_model()
                reload_model.assert_not_called()
                self.assertIsNotNone(run.update_id)
        run.pause()

    def test_reload_failure_keeps_original_engine_and_tree(self):
        old_fdm = self.app._controller.fdm
        old_tree = self.app.property_view.widget
        with patch.object(self.app._controller, "reload", return_value=False):
            with patch("jsbsim_gui.app.showerror") as error:
                self.app.reload_model()
                error.assert_called_once()
        self.assertIs(self.app._controller.fdm, old_fdm)
        self.assertIs(self.app.property_view.widget, old_tree)

    def test_reload_running_after_confirmation_resets_controls(self):
        run = self.app.simulation_controls
        run.run_ic()
        run.run()
        with patch("jsbsim_gui.app.askyesno", return_value=True) as confirm:
            self.app.reload_model()
        confirm.assert_called_once()
        self.assertIsNone(run.update_id)
        self.assertEqual(str(run.init_button["state"]), "normal")

    def test_cancel_model_change_preserves_workspace(self):
        self.files.current_file.is_modified = True
        old_controller = self.app._controller
        with patch("jsbsim_gui.project_files.askyesnocancel", return_value=None):
            result = self.app.open_file("unused.xml", "other", Controller.load_aircraft)
        self.assertIsNone(result)
        self.assertIs(self.app.editor, self.editor)
        self.assertIs(self.app._controller, old_controller)

    def test_failed_model_change_preserves_workspace(self):
        old_controller = self.app._controller
        result = self.app.open_file("unused.xml", "other", lambda controller, _: False)
        self.assertFalse(result)
        self.assertIs(self.app.editor, self.editor)
        self.assertIs(self.app._controller, old_controller)

    def test_failed_save_cancels_model_change(self):
        self.files.current_file.is_modified = True
        old_controller = self.app._controller
        with patch("jsbsim_gui.project_files.askyesnocancel", return_value=True):
            with patch.object(self.files, "save_all", return_value=False):
                result = self.app.open_file(
                    "unused.xml", "other", Controller.load_aircraft
                )
        self.assertIsNone(result)
        self.assertIs(self.app.editor, self.editor)
        self.assertIs(self.app._controller, old_controller)

    def test_controller_reload_restores_engine_on_parse_failure(self):
        controller = self.app._controller
        old_fdm = controller.fdm
        old_history = controller.property_history
        with patch.object(controller, "get_xml_trees", side_effect=OSError("bad file")):
            with self.assertRaises(OSError):
                controller.reload()
        self.assertIs(controller.fdm, old_fdm)
        self.assertIs(controller.property_history, old_history)


if __name__ == "__main__":
    unittest.main()
