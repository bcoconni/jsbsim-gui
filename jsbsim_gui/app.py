# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2026 Bertrand Coconnier
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <http://www.gnu.org/licenses/>

import importlib.resources
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter.constants import EW, NSEW
from tkinter.messagebox import askyesno, showerror
from typing import Callable
import xml.etree.ElementTree as et
from xml.parsers.expat import ExpatError

from PIL import Image, ImageTk

from . import __version__
from .consoles_panel import ConsolesPanel
from .controller import Controller
from .csv_tree import CsvTree
from .drag_n_drop import DnDCsvColumns, DnDProperties
from .edit_actions import REDO_SHORTCUT, SHORTCUT_MODIFIER, EditAction
from .file_state import FileState
from .find import FindWindow
from .hierarchical_tree import PropertyTree
from .menu_bar import MenuBar, RecentFiles
from .options import OptionsWindow
from .plotinfo_list import PlotInfoListOptionsTab
from .plots_view import PlotsView
from .project_files import ProjectFiles
from .simulation_controls import SimulationControls
from .source_editor import SourceEditor
from .textview import TextViewOptionsTab
from .widget import AutoClearLabel, LabeledWidget, widget_is_descendant


class App(tk.Tk):
    def __init__(self, root_dir: Path | None = None):
        super().__init__()
        self._consoles_panel: ConsolesPanel | None = None
        self._controller: Controller | None = None
        self._console_sash = tk.PanedWindow(
            self, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.RAISED
        )
        self._statusbar = AutoClearLabel(self)
        self.main: ttk.Frame | ttk.Label | None = None
        self.editor: SourceEditor | None = None
        self.project_files: ProjectFiles | None = None
        self._find_window: FindWindow | None = None
        self.title(f"JSBSim GUI {__version__}")
        self.resizable(False, False)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Flat.TButton", relief=tk.FLAT)

        if root_dir:
            self.root_dir = root_dir
            if not self.root_dir.exists():
                self.display_logo()
                showerror(
                    "Error", message=f'The directory "{self.root_dir}" does not exist'
                )
                sys.exit(1)
        else:
            try:
                self.root_dir = Controller.get_default_root_dir()
            except IOError as e:
                self.display_logo()
                showerror("Error", message=str(e))
                sys.exit(1)

        self.root_dir = self.root_dir.resolve()
        self.menubar = MenuBar(self)
        self.config(menu=self.menubar)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind_all(
            f"<{SHORTCUT_MODIFIER}-f>", lambda _event: self.edit_action(EditAction.FIND)
        )
        self.bind_all(
            f"<{REDO_SHORTCUT}>", lambda _event: self.edit_action(EditAction.REDO)
        )
        self.bind_all(f"<{SHORTCUT_MODIFIER}-r>", lambda _: self.reload_model())
        self.bind_all(f"<{SHORTCUT_MODIFIER}-q>", lambda _event: self.on_closing())

    def on_closing(self) -> None:
        project_files = self.project_files
        if project_files and not project_files.prompt_save_if_modified(
            "You have unsaved changes. Do you want to save them before exiting?"
        ):
            return
        if self._controller:
            self._controller.close()
            self._controller = None
        self.destroy()

    def show_options(self):
        options_window = OptionsWindow(self)
        options_window.add_option_tab(TextViewOptionsTab(options_window), "Editor")
        options_window.add_option_tab(PlotInfoListOptionsTab(options_window), "Plots")

    def display_logo(self) -> None:
        self.menubar.update_save_menu_state(False)

        with importlib.resources.path("jsbsim_gui", "resources") as base_dir:
            with Image.open(str(base_dir / "logo_JSBSIM_globe_410x429.bmp")) as image:
                resized_image = Image.new(
                    "RGB", size=(600, image.height), color="white"
                )
                resized_image.paste(image, ((600 - image.width) // 2, 0))
                logo_image = ImageTk.PhotoImage(resized_image)
                self.main = ttk.Label(self, image=logo_image)
                self.main.image = logo_image
                self.main.grid()

    def load_model_from_cmdline(self, model_name: str) -> None:
        filename = self.root_dir / "aircraft" / model_name / (model_name + ".xml")
        success = self.open_file(filename, model_name, Controller.load_aircraft)
        if success:
            self.menubar.enable_menus()
            return

        self.display_logo()
        showerror("Error", message=f'"{model_name}" is not an aircraft model')

    def load_script_from_cmdline(self, script_name: str) -> None:
        filename = self.root_dir / script_name
        try:
            success = self.open_file(filename, script_name, Controller.load_script)
            if success:
                self.menubar.enable_menus()
                return

            error_msg = f'"{script_name}" is not a script file'
        except FileNotFoundError:
            error_msg = f"Could not find file: {filename}"

        self.display_logo()
        showerror("Error", message=error_msg)

    def reload_model(self) -> None:
        assert self._controller is not None and self._consoles_panel is not None
        assert self.editor is not None and self.project_files is not None
        if self.project_files.has_modified_files():
            showerror("Reload Model", "Save all modified files before reloading.")
            return
        if self.simulation_controls.is_running:
            if not askyesno(
                "Reload Model",
                "Reloading will stop and reset the simulation. Continue?",
            ):
                return
            self.simulation_controls.pause()

        self._consoles_panel.reset()
        old_fdm = self._controller.fdm
        old_history = self._controller.property_history
        try:
            success = self._controller.reload()
            if success:
                self._close_find_window()
                self.project_files.refresh_model()
                self.editor.refresh_model(self.project_files.current_file)
                self._create_property_tree()
                self.plots_view.clear_simulation_plots()
                self.simulation_controls.reset_for_reload()
        except (
            OSError,
            et.ParseError,
            ExpatError,
            RuntimeError,
            ValueError,
            KeyError,
        ) as error:
            self._controller.fdm = old_fdm
            self._controller.property_history = old_history
            showerror("Reload Error", message=str(error))
            return
        if success:
            self._statusbar.set_text("Model reloaded.")
        else:
            showerror(
                "Reload Error",
                message="Failed to reload the model. Please check the console for errors.",
            )

    def _mark_reload_pending(self) -> None:
        self._statusbar.set_text("Files saved. Reload the model to apply changes.")

    def _create_property_tree(self) -> None:
        assert self._controller is not None
        if self.property_view.widget is not None:
            self.property_view.widget.destroy()
        root = self._controller.get_property_root()
        assert root is not None
        self.property_tree = PropertyTree(
            self.property_view, self._controller.get_property_list(), root
        )
        self.property_tree.tree.bind(f"<{SHORTCUT_MODIFIER}-f>", self._find_property)
        self.property_view.set_widget(self.property_tree)
        self.dnd_properties = DnDProperties(self.property_tree, self.plots_view)

    def _select_source_file(self, file_state: FileState) -> None:
        assert self.editor is not None and self.project_files is not None
        if file_state is not None:
            self.notebook.select(self.editor)
            self.project_files.select_file(file_state)
            self.editor.open_source_file(file_state)

    def _on_editor_file_opened(self, file_state: FileState) -> None:
        assert self.project_files is not None
        self.project_files.show_file(file_state.filepath)
        self._select_source_file(file_state)

    def _on_editor_modified(self, modified: bool) -> None:
        assert self.project_files is not None
        self.project_files.mark_current_modified(modified)

    def _get_editor_content(self) -> str:
        assert self.editor is not None
        return self.editor.get_content()

    def _on_invalid_file(self, file_state: FileState, column: int, line: int) -> None:
        assert self.editor is not None
        self.editor.move_to(file_state, True, column, line)

    def _close_find_window(self) -> None:
        if self._find_window is not None and self._find_window.winfo_exists():
            self._find_window.destroy()
        self._find_window = None

    def _open_find_window(self) -> FindWindow:
        assert self._controller is not None
        assert self.project_files is not None and self.editor is not None
        editor = self.editor
        if self._find_window is not None and self._find_window.winfo_exists():
            self._find_window.lift()
        else:
            self._find_window = FindWindow(
                self,
                self._controller,
                self.project_files.get_file_states(),
                editor.select_text,
                lambda file_state, col, line: editor.move_to(
                    file_state, True, col, line
                ),
            )
        return self._find_window

    def _find_property(self, _: tk.Event | None) -> str:
        names = self.property_tree.get_selected_property_names(False)
        find_window = self._open_find_window()
        if len(names) == 1:
            find_window.find_property(names[0])
        return "break"

    def _on_csv_toggle(self, collapsed: bool) -> None:
        self.left_frame.grid_rowconfigure(1, weight=1 if collapsed else 2)
        self.left_frame.grid_rowconfigure(2, weight=0 if collapsed else 1)

    def _update_simulation(self) -> None:
        assert self._controller is not None
        self.property_tree.update_values()
        self.plots_view.update_plots()
        sim_time = self._controller.fdm.get_sim_time()
        self._statusbar.set_text(f"Simulated time: {sim_time:.3f}s")

    def _update_properties(self, _) -> None:
        assert self._controller is not None
        sim_time = self.plots_view.t_hover
        if sim_time:
            properties = self.property_tree.get_visible_properties()
            values = self._controller.get_time_snapshot(sim_time, properties)
            self.property_tree.update_values(values)
        else:
            self.property_tree.update_values()
            sim_time = self._controller.fdm.get_sim_time()
        self._statusbar.set_text(f"Simulated time: {sim_time:.3f}s")

    def edit(self) -> None:
        add_options: dict[str, int | ConsolesPanel] = {}
        self._close_find_window()
        if self.main:
            if isinstance(self.main, ttk.Frame):
                self._console_sash.remove(self.main)
                add_options["width"] = self.main.winfo_width()
                add_options["height"] = self.main.winfo_height()
            self.main.destroy()

        assert self._controller is not None
        self.main = ttk.Frame(self._console_sash)
        self._workspace_sash = tk.PanedWindow(
            self.main, orient=tk.HORIZONTAL, sashwidth=4, sashrelief=tk.RAISED
        )
        self.left_frame = ttk.Frame(self._workspace_sash)
        self.notebook = ttk.Notebook(self._workspace_sash)
        self.project_files = ProjectFiles(
            self.left_frame,
            self._controller,
            self._select_source_file,
            self._get_editor_content,
            self._on_invalid_file,
            self.mark_title_modified,
            self._mark_reload_pending,
        )
        self.project_files.grid(column=0, row=0, sticky=NSEW)
        self.editor = SourceEditor(
            self.notebook,
            self.project_files.current_file,
            self._on_editor_file_opened,
            self._on_editor_modified,
        )
        self.editor.bind(f"<{SHORTCUT_MODIFIER}-s>", lambda e: self.save_file())
        self.notebook.add(self.editor, text="Editor")
        self.plots_view = PlotsView(self.notebook, self._controller)
        self.notebook.add(self.plots_view, text="Plots")

        self.property_view = LabeledWidget(self.left_frame, "Property Explorer")
        self.property_view.grid(column=0, row=1, sticky=NSEW)
        self._create_property_tree()

        self.csv_view = LabeledWidget(
            self.left_frame, "CSV Data", collapsable=True, on_toggle=self._on_csv_toggle
        )
        self.csv_tree = CsvTree(self.csv_view)
        self.csv_view.set_widget(self.csv_tree)
        self.csv_view.grid(column=0, row=2, sticky=NSEW)
        self.csv_view.grid_remove()
        self.dnd_csv_columns = DnDCsvColumns(self.csv_tree, self.plots_view)

        self.simulation_controls = SimulationControls(
            self.left_frame,
            self._controller,
            self._update_simulation,
            lambda: self._update_properties(None),
        )
        self.simulation_controls.grid(column=0, row=3, sticky=EW, pady=(4, 0))
        self.plots_view.bind_motion_handler(self._update_properties)

        self._workspace_sash.add(self.left_frame)
        self._workspace_sash.add(self.notebook, stretch="always")
        self._workspace_sash.grid(column=0, row=0, sticky=NSEW)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        assert self._consoles_panel
        self._console_sash.add(
            self.main, before=self._consoles_panel, stretch="always", **add_options
        )
        self.menubar.update_save_menu_state(True)

        # Window layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _on_file_link_click(self, rel_path: Path, line: int) -> None:
        if self.editor is None or self.project_files is None:
            return
        file_state = self.project_files.get_file_state(rel_path)
        if file_state is not None:
            self.editor.move_to(file_state, True, 0, line)

    def mark_title_modified(self, is_modified: bool) -> None:
        current_title = self.title()
        if current_title.endswith("*"):
            current_title = current_title[:-1]
        if is_modified:
            self.title(current_title + "*")
        else:
            self.title(current_title)

    def save_file(self) -> None:
        if self.project_files is not None:
            self.project_files.save_file()

    def save_all(self) -> None:
        if self.project_files is not None:
            self.project_files.save_all()

    def load_csv(self, path: Path) -> None:
        if self.editor is None:
            showerror(
                "Error",
                message="Please open an aircraft or script before loading a CSV file.",
            )
            return
        was_empty = not self.csv_tree.has_loaded_files()
        self.csv_tree.load_csv(path)
        if was_empty and self.csv_tree.has_loaded_files():
            self.csv_view.grid()
            self._on_csv_toggle(False)

    def edit_action(self, action: EditAction) -> None:
        if self.editor is None or self.project_files is None:
            return
        focused = self.focus_get()
        if action == EditAction.FIND:
            if widget_is_descendant(focused, self.property_view):
                self._find_property(None)
            else:
                self._open_find_window()
        elif widget_is_descendant(focused, self.property_view):
            self.property_view.apply_edit_action(action)
        elif widget_is_descendant(focused, self.project_files):
            self.project_files.apply_edit_action(action)
        elif self.notebook.select() == str(self.plots_view):
            self.plots_view.apply_edit_action(action)
        else:
            self.editor.apply_edit_action(action)

    def open_file(
        self,
        filename: Path,
        aircraft_name: str,
        load_file: Callable[[Controller, Path], bool],
    ) -> bool | None:
        project_files = self.project_files
        if project_files and not project_files.prompt_save_if_modified(
            "You have unsaved changes. Do you want to save them before opening another model?"
        ):
            return None
        if self._consoles_panel:
            self._consoles_panel.reset()
        else:
            self._consoles_panel = ConsolesPanel(
                self._console_sash,
                on_file_link_click=self._on_file_link_click,
                height=8,
            )
            self._console_sash.add(self._consoles_panel, stretch="never")

        console_logger = self._consoles_panel.get_logger(
            lambda name: name.relative_to(self.root_dir)
        )

        old_controller = self._controller
        controller = Controller(self.root_dir, console_logger)
        success = False
        try:
            success = load_file(controller, filename)
        finally:
            if not success:
                controller.close()
                if old_controller:
                    old_controller.activate_logger()

        if success:
            if old_controller:
                old_controller.close()
                controller.activate_logger()
            self._controller = controller
            self.resizable(True, True)
            self.title(f"JSBSim GUI {__version__} - {aircraft_name}")
            self.edit()
            self._console_sash.grid(column=0, row=0, sticky=NSEW)
            self._statusbar.grid(column=0, row=1, sticky=EW)
            self._statusbar.set_text("Ready.")
            RecentFiles().add_recent_file(filename, self.root_dir)
        return success
