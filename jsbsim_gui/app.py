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

import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter.constants import EW, NSEW
from tkinter.messagebox import askyesnocancel, showerror
from typing import Callable, Dict, Optional

from PIL import Image, ImageTk

from . import __version__
from .consoles_panel import ConsolesPanel
from .controller import Controller, get_path_relative_to_root
from .edit_actions import REDO_SHORTCUT, SHORTCUT_MODIFIER, EditableFrame, EditAction
from .menu_bar import MenuBar
from .run import Run
from .source_editor import SourceEditor
from .widget import AutoClearLabel


class App(tk.Tk):
    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self._consoles_panel: Optional[ConsolesPanel] = None
        self._controller: Optional[Controller] = None
        self._console_sash = tk.PanedWindow(
            self, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.RAISED
        )
        self._statusbar = AutoClearLabel(self)
        self.main: EditableFrame | ttk.Label | None = None
        self.title(f"JSBSim GUI {__version__}")
        self.resizable(False, False)
        self._style = ttk.Style()
        self._style.theme_use("clam")

        if root_dir:
            self.root_dir = root_dir
            if not os.path.exists(self.root_dir):
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

        self.root_dir = os.path.realpath(self.root_dir)
        self.menubar = MenuBar(self, self.root_dir)
        self.config(menu=self.menubar)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind_all(
            f"<{SHORTCUT_MODIFIER}-f>", lambda _event: self.edit_action(EditAction.FIND)
        )
        self.bind_all(
            f"<{REDO_SHORTCUT}>", lambda _event: self.edit_action(EditAction.REDO)
        )
        self.bind_all(f"<{SHORTCUT_MODIFIER}-q>", lambda _event: self.on_closing())
        self.bind_all(
            f"<{SHORTCUT_MODIFIER}-r>", lambda _event: self.reload_controller()
        )

    def on_closing(self) -> None:
        if not self._prompt_save_if_modified(
            "You have unsaved changes. Do you want to save them before exiting?"
        ):
            return
        if self._controller:
            self._controller.close()
            self._controller = None
        self.destroy()

    def _prompt_save_if_modified(self, message: str) -> bool:
        if isinstance(self.main, SourceEditor) and self.main.has_modified_files():
            result = askyesnocancel("Unsaved Changes", message=message)
            if result is None:
                return False
            elif result:
                if not self.main.save_all():
                    return False
        return True

    def display_logo(self) -> None:
        self.menubar.update_save_menu_state(False)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "resources", "logo_JSBSIM_globe_410x429.bmp")
        with Image.open(logo_path) as image:
            resized_image = Image.new("RGB", size=(600, image.height), color="white")
            resized_image.paste(image, ((600 - image.width) // 2, 0))
            logo_image = ImageTk.PhotoImage(resized_image)
            self.main = ttk.Label(self, image=logo_image)
            self.main.image = logo_image
            self.main.grid()

    def load_model_from_cmdline(self, model_name: str) -> None:
        filename = os.path.join(
            self.root_dir, "aircraft", model_name, model_name + ".xml"
        )
        success = self.open_file(filename, model_name, Controller.load_aircraft)
        if success:
            self.menubar.enable_menus()
            return

        self.display_logo()
        showerror("Error", message=f'"{model_name}" is not an aircraft model')

    def load_script_from_cmdline(self, script_name: str) -> None:
        filename = os.path.join(self.root_dir, script_name)
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

    def run(self) -> None:
        assert self.main
        assert self._controller

        has_modified_files = (
            isinstance(self.main, SourceEditor) and self.main.has_modified_files()
        )

        if not self._prompt_save_if_modified(
            "You have unsaved changes. Do you want to save them before switching to run view?"
        ):
            return

        if has_modified_files and not self.reload_controller():
            return

        w = self.main.winfo_width()
        h = self.main.winfo_height()
        self._console_sash.remove(self.main)
        self.main.destroy()
        self.menubar.update_save_menu_state(False)
        self.main = Run(self._console_sash, self._controller, self._statusbar)
        self._console_sash.add(
            self.main, before=self._consoles_panel, width=w, height=h
        )

        # Window layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def reload_controller(self) -> bool:
        assert self._controller is not None and self._consoles_panel is not None
        self._consoles_panel.reset()
        if self._controller.reload():
            self._statusbar.set_text("Model reloaded.")
            return True

        showerror(
            "Reload Error",
            message="Failed to reload the model. Please check the console for errors.",
        )
        return False

    def edit(self) -> None:
        add_options: Dict[str, int | ConsolesPanel] = {}
        if self.main:
            if isinstance(self.main, EditableFrame):
                assert self._consoles_panel
                self._console_sash.remove(self.main)
                add_options["width"] = self.main.winfo_width()
                add_options["height"] = self.main.winfo_height()
                add_options["before"] = self._consoles_panel
            self.main.destroy()

        # Open the file in a text widget
        assert self._controller is not None
        self.main = SourceEditor(
            self._console_sash,
            self._controller,
            self.mark_title_modified,
            self.reload_controller,
        )
        self._console_sash.add(self.main, **add_options)
        self.menubar.update_save_menu_state(True)

        # Window layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _on_file_link_click(self, rel_path: str, line: int) -> None:
        if not isinstance(self.main, SourceEditor):
            self.edit()
        assert isinstance(self.main, SourceEditor)
        file_state = self.main.file_states.get(rel_path)
        if file_state is not None:
            self.main.move_to(file_state, True, 0, line)

    def mark_title_modified(self, is_modified: bool) -> None:
        current_title = self.title()
        if current_title.endswith("*"):
            current_title = current_title[:-1]
        if is_modified:
            self.title(current_title + "*")
        else:
            self.title(current_title)

    def save_file(self) -> None:
        if isinstance(self.main, SourceEditor):
            self.main.save_file()

    def save_all(self) -> None:
        if isinstance(self.main, SourceEditor):
            self.main.save_all()

    def load_csv(self, path: str) -> None:
        if not isinstance(self.main, Run):
            if self._controller is None:
                showerror(
                    "Error",
                    message="Please open an aircraft or script before loading a CSV file.",
                )
                return
            self.run()
        if isinstance(self.main, Run):
            self.main.load_csv(path)

    def edit_action(self, action: EditAction) -> None:
        if self.main is not None:
            self.main.apply_edit_action(action)

    def open_file(
        self,
        filename: str,
        aircraft_name: str,
        load_file: Callable[[Controller, str], bool],
    ) -> bool:
        self.resizable(True, True)
        self.title(f"JSBSim GUI {__version__} - {aircraft_name}")

        if self._consoles_panel:
            self._consoles_panel.destroy()

        self._consoles_panel = ConsolesPanel(
            self._console_sash, on_file_link_click=self._on_file_link_click, height=10
        )
        console_logger = self._consoles_panel.get_logger(
            lambda name: get_path_relative_to_root(name, self.root_dir)
        )

        if self._controller:
            self._controller.close()

        self._controller = Controller(self.root_dir, console_logger)
        success = load_file(self._controller, filename)

        if success:
            self.edit()
            self._console_sash.add(self._consoles_panel)
            self._console_sash.grid(column=0, row=0, sticky=NSEW)
            self._statusbar.grid(column=0, row=1, sticky=EW)
            self._statusbar.set_text("Ready.")
        else:
            self._controller.close()
            self._controller = None  # Delete the FGFDMExec instance.

        return success
