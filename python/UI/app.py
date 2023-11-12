# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023 Bertrand Coconnier
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
from tkinter import ttk
from tkinter.constants import NSEW
from tkinter.messagebox import showerror
from typing import Callable, Optional

from PIL import Image, ImageTk

from .controller import Controller
from .source_editor import SourceEditor


class MenuBar(tk.Menu):
    def __init__(self, master: tk.Widget, root_dir: str):
        super().__init__(master)
        self.root_dir = root_dir

        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="Open...", command=self.select_script_file)
        file_menu.add_command(label="Exit", command=master.destroy)
        self.add_cascade(label="File", menu=file_menu)

    def select_script_file(self) -> None:
        filename = fd.askopenfilename(
            title="Open a script / aircraft",
            initialdir=self.root_dir,
            filetypes=(("script files", "*.xml"),),
        )
        if filename:
            root = et.parse(filename).getroot()
            if root.tag == "runscript":
                self.master.open_file(filename, Controller.load_script)
            elif root.tag == 'fdm_config':
                self.master.open_file(filename, Controller.load_aircraft)
            else:
                name = os.path.relpath(filename, self.root_dir)
                showerror(
                    "Error",
                    message=f'The file "{name}" is neither a JSBSim script nor an aircraft',
                )


class App(tk.Tk):
    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.title(f"JSBSim {Controller.get_version()}")
        self.resizable(False, False)
        self.controller: Optional[Controller] = None

        menubar = MenuBar(self, root_dir)
        self.config(menu=menubar)

        with Image.open("logo_JSBSIM_globe.png") as image:
            logo_resized = image.resize((image.width * 400 // image.height, 400))
            logo_image = ImageTk.PhotoImage(logo_resized)
            self.main = ttk.Label(self, image=logo_image, background="white")
            self.main.image = logo_image
            self.main.grid(padx=(600 - logo_resized.width) // 2)

        if root_dir:
            self.root_dir = root_dir
        else:
            try:
                self.root_dir = Controller.get_default_root_dir()
            except IOError as e:
                showerror("Error", message=e)
                self.destroy()

    def open_file(self, filename: str, load_file:Callable[[Controller,str], None])->None:
        self.resizable(True, True)
        # Remove the logo
        self.main.destroy()

        def initialize_controller(aircraft_name: str, widget: tk.Widget) -> Controller:
            self.controller = Controller(self.root_dir, widget)
            load_file(self.controller, aircraft_name)
            return self.controller

        # Open the file in an text widget
        script_relpath = os.path.relpath(filename, self.root_dir)
        self.title(f"JSBSim {Controller.get_version()} - {script_relpath}")
        self.main = SourceEditor(self, filename, self.root_dir, initialize_controller)

        # Window layout
        self.main.grid(column=0, row=0, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
