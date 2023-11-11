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
from tkinter import filedialog as fd
from tkinter.messagebox import showerror

from jsbsim.UI.controller import Controller
from PIL import Image, ImageTk


class MenuBar(tk.Menu):
    def __init__(self, root, root_dir):
        super().__init__(root)
        self.root_dir = root_dir

        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="Open...", command=self.select_script_file)
        file_menu.add_command(label="Exit", command=root.destroy)
        self.add_cascade(label="File", menu=file_menu)

    def select_script_file(self):
        filename = fd.askopenfilename(
            title="Open a script",
            initialdir=self.root_dir,
            filetypes=(("script files", "*.xml"),),
        )
        if filename:
            self.master.open(filename)


class Editor(tk.Text):
    def __init__(self, root: tk.Widget, text: str):
        super().__init__(root, width=80, height=40, wrap="none")
        self.insert("1.0", text)
        xs = tk.Scrollbar(root, orient="horizontal", command=self.xview)
        ys = tk.Scrollbar(root, orient="vertical", command=self.yview)
        self["xscrollcommand"] = xs.set
        self["yscrollcommand"] = ys.set
        self.grid(column=0, row=0, sticky="nwes")
        xs.grid(column=0, row=1, sticky="we")
        ys.grid(column=1, row=0, sticky="ns")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        # Read only
        self["state"] = "disabled"


class App(tk.Tk):
    def __init__(self, root_dir=None):
        super().__init__()
        self.title(f"JSBSim {Controller.get_version()}")
        self.resizable(False, False)

        menubar = MenuBar(self, root_dir)
        self.config(menu=menubar)

        with Image.open("logo_JSBSIM_globe.png") as image:
            logo_resized = image.resize((image.width * 400 // image.height, 400))
            logo_image = ImageTk.PhotoImage(logo_resized)
            self.logo = tk.Label(self, image=logo_image, width=600, background="white")
            self.logo.image = logo_image
            self.logo.pack()

        if root_dir:
            self.root_dir = root_dir
        else:
            try:
                self.root_dir = Controller.get_default_root_dir()
            except IOError as e:
                showerror("Error", message=e)
                self.destroy()

    def open(self, filename):
        self.resizable(True, True)
        self.logo.destroy()
        relpath = os.path.relpath(filename, self.root_dir)

        with open(filename, "r") as f:
            self.title(f"JSBSim {Controller.get_version()} - {relpath}")
            self.editor = Editor(self, "".join(f.readlines()))
