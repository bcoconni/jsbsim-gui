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

import os
import tkinter as tk
import xml.etree.ElementTree as et
from tkinter import filedialog as fd
from tkinter.messagebox import showerror

from .controller import Controller
from .edit_actions import EditAction


class MenuBar(tk.Menu):
    def __init__(self, master: tk.Widget, root_dir: str):
        super().__init__(master)
        self.root_dir = root_dir

        self.file_menu = tk.Menu(self, tearoff=False)
        self.file_menu.add_command(label="Root...", command=self.set_root_dir)
        self.file_menu.add_command(label="Open...", command=self.select_script_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Save",
            accelerator="Ctrl+S",
            command=master.save_file,
            state=tk.DISABLED,
        )
        self.file_menu.add_command(
            label="Save All", command=master.save_all, state=tk.DISABLED
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=master.on_closing)
        self.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(self, tearoff=False)
        self.edit_menu.add_command(
            label="Undo",
            accelerator="Ctrl+Z",
            command=lambda: master.edit_action(EditAction.UNDO),
        )
        self.edit_menu.add_command(
            label="Redo",
            accelerator="Ctrl+Y",
            command=lambda: master.edit_action(EditAction.REDO),
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Select All",
            accelerator="Ctrl+A",
            command=lambda: master.edit_action(EditAction.SELECT_ALL),
        )
        self.edit_menu.add_command(
            label="Cut",
            accelerator="Ctrl+X",
            command=lambda: master.edit_action(EditAction.CUT),
        )
        self.edit_menu.add_command(
            label="Copy",
            accelerator="Ctrl+C",
            command=lambda: master.edit_action(EditAction.COPY),
        )
        self.edit_menu.add_command(
            label="Paste",
            accelerator="Ctrl+V",
            command=lambda: master.edit_action(EditAction.PASTE),
        )
        self.add_cascade(label="Edit", menu=self.edit_menu)
        self.entryconfig("Edit", state=tk.DISABLED)

        view_menu = tk.Menu(self, tearoff=False)
        view_menu.add_command(label="Edit", command=self.master.edit)
        view_menu.add_command(label="Run", command=self.master.run)
        self.add_cascade(label="View", menu=view_menu)
        self.entryconfig("View", state=tk.DISABLED)

    def select_script_file(self) -> None:
        filename = fd.askopenfilename(
            title="Open a script / aircraft",
            initialdir=self.root_dir,
            filetypes=(("script files", "*.xml"),),
        )
        if filename:
            root = et.parse(filename).getroot()
            success = False
            if root.tag == "runscript":
                use_el = root.find("use")
                aircraft_name = use_el.attrib["aircraft"]
                success = self.master.open_file(
                    filename, aircraft_name, Controller.load_script
                )
            elif root.tag == "fdm_config":
                aircraft_name = os.path.splitext(os.path.basename(filename))[0]
                success = self.master.open_file(
                    filename, aircraft_name, Controller.load_aircraft
                )

            if success:
                self.entryconfig("Edit", state=tk.NORMAL)
                self.entryconfig("View", state=tk.NORMAL)
            else:
                name = os.path.relpath(filename, self.root_dir)
                showerror(
                    "Error",
                    message=f'The file "{name}" is neither a JSBSim script nor an aircraft',
                )

    def set_root_dir(self) -> None:
        directory = fd.askdirectory(
            title="Select Root Directory",
            initialdir=self.root_dir,
        )
        if directory:
            self.root_dir = directory
            self.master.root_dir = directory

    def update_save_menu_state(self, enable: bool) -> None:
        state = tk.NORMAL if enable else tk.DISABLED
        self.file_menu.entryconfig("Save", state=state)
        self.file_menu.entryconfig("Save All", state=state)
        self.entryconfig("Edit", state=state)
