# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
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

import tkinter as tk
import xml.etree.ElementTree as et
from pathlib import Path
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from .controller import Controller
from .edit_actions import REDO_SHORTCUT, SHORTCUT_MODIFIER, EditAction
from .recent_files import RecentFiles

if TYPE_CHECKING:
    from .app import App

OPEN_RECENT_MENU_ENTRY = "Open Recent"
RELOAD_MENU_ENTRY = "Reload"
SAVE_MENU_ENTRY = "Save"
SAVE_ALL_MENU_ENTRY = "Save All"
EDIT_MENU_ENTRY = "Edit"


def open_file(app: "App", filename: Path) -> bool | None:
    root = et.parse(filename).getroot()
    success = False
    if root.tag == "runscript":
        use_el = root.find("use")
        if use_el is not None:
            aircraft_name = use_el.attrib["aircraft"]
            success = app.open_file(filename, aircraft_name, Controller.load_script)
    elif root.tag == "fdm_config":
        aircraft_name = filename.stem
        success = app.open_file(filename, aircraft_name, Controller.load_aircraft)

    if success:
        app.menubar.enable_menus()

    return success


class MenuBar(ttk.Menu):
    def __init__(self, master: "App"):
        super().__init__(master)

        self._file_menu = ttk.Menu(self, tearoff=False)
        self._file_menu.add_command(label="Root...", command=self._set_root_dir)
        self._file_menu.add_command(label="Open...", command=self._select_script_file)
        sub_menu = RecentFiles().menu(self._file_menu, self._open_recent_file)
        self._file_menu.add_cascade(label=OPEN_RECENT_MENU_ENTRY, menu=sub_menu)
        self._file_menu.add_separator()
        self._file_menu.add_command(
            label=RELOAD_MENU_ENTRY,
            accelerator=f"{SHORTCUT_MODIFIER}+R",
            command=master.reload_model,
            state=tk.DISABLED,
        )
        self._file_menu.add_command(
            label=SAVE_MENU_ENTRY,
            accelerator=f"{SHORTCUT_MODIFIER}+S",
            command=master.save_file,
            state=tk.DISABLED,
        )
        self._file_menu.add_command(
            label=SAVE_ALL_MENU_ENTRY, command=master.save_all, state=tk.DISABLED
        )
        self._file_menu.add_separator()
        self._file_menu.add_command(
            label="Exit",
            accelerator=f"{SHORTCUT_MODIFIER}+Q",
            command=master.on_closing,
        )
        self.add_cascade(label="File", menu=self._file_menu)

        edit_menu = ttk.Menu(self, tearoff=False)
        edit_menu.add_command(
            label="Undo",
            accelerator=f"{SHORTCUT_MODIFIER}+Z",
            command=lambda: master.edit_action(EditAction.UNDO),
        )
        edit_menu.add_command(
            label="Redo",
            accelerator=REDO_SHORTCUT,
            command=lambda: master.edit_action(EditAction.REDO),
        )
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Select All",
            accelerator=f"{SHORTCUT_MODIFIER}+A",
            command=lambda: master.edit_action(EditAction.SELECT_ALL),
        )
        edit_menu.add_command(
            label="Cut",
            accelerator=f"{SHORTCUT_MODIFIER}+X",
            command=lambda: master.edit_action(EditAction.CUT),
        )
        edit_menu.add_command(
            label="Copy",
            accelerator=f"{SHORTCUT_MODIFIER}+C",
            command=lambda: master.edit_action(EditAction.COPY),
        )
        edit_menu.add_command(
            label="Paste",
            accelerator=f"{SHORTCUT_MODIFIER}+V",
            command=lambda: master.edit_action(EditAction.PASTE),
        )
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Find...",
            accelerator=f"{SHORTCUT_MODIFIER}+F",
            command=lambda: master.edit_action(EditAction.FIND),
        )
        edit_menu.add_separator()
        edit_menu.add_command(label="Options...", command=lambda: master.show_options())
        self.add_cascade(label=EDIT_MENU_ENTRY, menu=edit_menu)
        self.entryconfig(EDIT_MENU_ENTRY, state=tk.DISABLED)

    def _select_script_file(self) -> None:
        from .app import App

        assert isinstance(self.master, App)
        filename = ttk.Querybox.get_open_filename(
            self.master,
            initialdir=self.master.root_dir,
            filetypes=(
                ("script and aircraft files", "*.xml"),
                ("CSV files", "*.csv"),
            ),
        )
        if not filename:
            return

        file_path = Path(filename).resolve()
        if filename.lower().endswith(".csv"):
            self.master.load_csv(file_path)
            return

        self._open_file(file_path)

    def _open_recent_file(self, filename: Path, root_dir: Path) -> None:
        from .app import App

        assert isinstance(self.master, App)
        self.master.root_dir = root_dir
        self._open_file(filename)

    def _open_file(self, filename: Path) -> None:
        from .app import App

        assert isinstance(self.master, App)
        success = open_file(self.master, filename)

        if success is False:
            name = filename.relative_to(self.master.root_dir)
            ttk.Messagebox.show_error(
                parent=self.master,
                title="Error",
                message=f'The file "{name}" is neither a JSBSim script nor an aircraft',
            )

    def _set_root_dir(self) -> None:
        from .app import App

        assert isinstance(self.master, App)
        directory = ttk.Querybox.get_directory(
            self.master, initialdir=self.master.root_dir
        )
        if directory:
            self.master.root_dir = Path(directory).resolve()

    def enable_menus(self):
        self.entryconfig(EDIT_MENU_ENTRY, state=tk.NORMAL)
        self._file_menu.entryconfig(RELOAD_MENU_ENTRY, state=tk.NORMAL)
        sub_menu = RecentFiles().menu(self._file_menu, self._open_recent_file)
        self._file_menu.entryconfigure(OPEN_RECENT_MENU_ENTRY, menu=sub_menu)

    def update_save_menu_state(self, enable: bool) -> None:
        state = tk.NORMAL if enable else tk.DISABLED
        self._file_menu.entryconfig(SAVE_MENU_ENTRY, state=state)
        self._file_menu.entryconfig(SAVE_ALL_MENU_ENTRY, state=state)
