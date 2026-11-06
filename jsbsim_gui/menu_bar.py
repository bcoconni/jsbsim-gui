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

import json
import os
import tkinter as tk
import xml.etree.ElementTree as et
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog as fd
from tkinter.messagebox import showerror
from typing import Callable

import platformdirs

from .controller import Controller
from .edit_actions import REDO_SHORTCUT, SHORTCUT_MODIFIER, EditAction
from .options import get_options

FILE_MANAGEMENT_KEY = "file_management"
RECENT_FILES_KEY = "recent_files"
OPEN_RECENT_MENU_ENTRY = "Open recent"


@dataclass
class FileManagementOptions:
    num_recent_files: int = 5


class RecentFiles:
    def __init__(self) -> None:
        options = get_options().get(FILE_MANAGEMENT_KEY)
        self._file_options = FileManagementOptions(**options)

        self._recent_files_path = (
            Path(platformdirs.user_config_dir("jsbsim-gui")) / "recent_files.json"
        )
        self._recent_files: list[list[str]] = []
        self._get_recent_file_list()

    def add_recent_file(self, file_path: str, root_dir: str):
        num_recent_files = self._file_options.num_recent_files
        new_entry = [file_path, root_dir]
        try:
            index = self._recent_files.index(new_entry)
            if index == 0:
                return

            if index + 1 == num_recent_files:
                self._recent_files = [new_entry] + self._recent_files[:-1]
            else:
                before = self._recent_files[:index]
                after = self._recent_files[index + 1 :]
                self._recent_files = [new_entry] + before + after
        except ValueError:
            if len(self._recent_files) >= num_recent_files:
                self._recent_files = [new_entry] + self._recent_files[:num_recent_files]
            else:
                self._recent_files = [new_entry] + self._recent_files

        self._recent_files_path.parent.mkdir(parents=True, exist_ok=True)
        data = {RECENT_FILES_KEY: self._recent_files}
        with open(self._recent_files_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _get_recent_file_list(self):
        if not self._recent_files_path.exists():
            self._recent_files = []
            return

        with open(self._recent_files_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                self._recent_files = data[RECENT_FILES_KEY]
                num_recent_files = self._file_options.num_recent_files
                if len(self._recent_files) > num_recent_files:
                    self._recent_files = self._recent_files[:num_recent_files]

    def get_menu(
        self, master: tk.Widget, open_file: Callable[[str, str], None]
    ) -> tk.Menu:
        menu = tk.Menu(master, tearoff=False)

        def generate_menu_command(file: list[str]):  # Capture the value of `file`
            def menu_command(
                menu: tk.Menu, file_name: Path, open_file: Callable[[str, str], None]
            ):
                menu.add_command(label=str(file_name), command=lambda: open_file(*file))

            return menu_command

        for file in self._recent_files:
            file_name = Path(file[0]).resolve()
            try:
                home = Path.home()
                if file_name.is_relative_to(home):
                    file_name = "~" / file_name.relative_to(home)
            except RuntimeError:
                pass

            menu_add_command = generate_menu_command(file)
            menu_add_command(menu, file_name, open_file)

        return menu


class MenuBar(tk.Menu):
    def __init__(self, master: tk.Tk, root_dir: str):
        super().__init__(master)
        self._root_dir = root_dir

        self._file_menu = tk.Menu(self, tearoff=False)
        self._file_menu.add_command(label="Root...", command=self._set_root_dir)
        self._file_menu.add_command(label="Open...", command=self._select_script_file)
        sub_menu = RecentFiles().get_menu(self._file_menu, self._open_recent_file)
        self._file_menu.add_cascade(label=OPEN_RECENT_MENU_ENTRY, menu=sub_menu)
        self._file_menu.add_separator()
        self._file_menu.add_command(
            label="Save",
            accelerator=f"{SHORTCUT_MODIFIER}+S",
            command=master.save_file,
            state=tk.DISABLED,
        )
        self._file_menu.add_command(
            label="Save All", command=master.save_all, state=tk.DISABLED
        )
        self._file_menu.add_command(
            label="Reload",
            accelerator=f"{SHORTCUT_MODIFIER}+R",
            command=master.reload_model,
            state=tk.DISABLED,
        )
        self._reload_menu_index = self._file_menu.index(tk.END)
        self._file_menu.add_separator()
        self._file_menu.add_command(
            label="Exit",
            accelerator=f"{SHORTCUT_MODIFIER}+Q",
            command=master.on_closing,
        )
        self.add_cascade(label="File", menu=self._file_menu)

        edit_menu = tk.Menu(self, tearoff=False)
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
        self.add_cascade(label="Edit", menu=edit_menu)
        self.entryconfig("Edit", state=tk.DISABLED)

    def _select_script_file(self) -> None:
        filename = fd.askopenfilename(
            title="Open a script, aircraft or CSV file",
            initialdir=self._root_dir,
            filetypes=(
                ("script and aircraft files", "*.xml"),
                ("CSV files", "*.csv"),
            ),
        )
        if not filename:
            return

        if filename.lower().endswith(".csv"):
            self.master.load_csv(filename)
            return

        self._open_file(filename)

    def _open_recent_file(self, filename: str, root_dir: str) -> None:
        self._root_dir = root_dir
        self.master.root_dir = root_dir
        self._open_file(filename)

    def _open_file(self, filename: str) -> None:
        root = et.parse(filename).getroot()
        success = False
        if root.tag == "runscript":
            use_el = root.find("use")
            if use_el is not None:
                aircraft_name = use_el.attrib["aircraft"]
                success = self.master.open_file(
                    filename, aircraft_name, Controller.load_script
                )
        elif root.tag == "fdm_config":
            aircraft_name = os.path.splitext(os.path.basename(filename))[0]
            success = self.master.open_file(
                filename, aircraft_name, Controller.load_aircraft
            )

        if success is None:
            return
        if success:
            self.enable_menus()
            sub_menu = RecentFiles().get_menu(self._file_menu, self._open_recent_file)
            self._file_menu.entryconfigure(OPEN_RECENT_MENU_ENTRY, menu=sub_menu)
        else:
            name = os.path.relpath(filename, self._root_dir)
            showerror(
                "Error",
                message=f'The file "{name}" is neither a JSBSim script nor an aircraft',
            )

    def _set_root_dir(self) -> None:
        directory = fd.askdirectory(
            title="Select Root Directory",
            initialdir=self._root_dir,
        )
        if directory:
            self._root_dir = directory
            self.master.root_dir = directory

    def enable_menus(self):
        assert self._reload_menu_index is not None
        self.entryconfig("Edit", state=tk.NORMAL)
        self._file_menu.entryconfig(self._reload_menu_index, state=tk.NORMAL)

    def update_save_menu_state(self, enable: bool) -> None:
        state = tk.NORMAL if enable else tk.DISABLED
        self._file_menu.entryconfig("Save", state=state)
        self._file_menu.entryconfig("Save All", state=state)
