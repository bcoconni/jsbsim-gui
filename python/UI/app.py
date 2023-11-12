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

import ctypes
import os
import sys
import tkinter as tk
from contextlib import contextmanager
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter.constants import EW, NONE, NS, NSEW
from tkinter.messagebox import showerror
from typing import Callable, Optional

from PIL import Image, ImageTk

from .controller import Controller
from .hierarchical_tree import FileTree, PropertyTree
from .textview import Console, TextView


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
            title="Open a script",
            initialdir=self.root_dir,
            filetypes=(("script files", "*.xml"),),
        )
        if filename:
            self.master.open_script(filename)


class SourceEditor(tk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        filename: str,
        root_dir: str,
        get_controller: Callable[[str, tk.Widget], Controller],
    ):
        super().__init__(master)
        self.root_dir = root_dir
        frame = ttk.Frame(self)
        left_frame = ttk.Frame(frame)

        self.console = Console(self, height=10)
        self.controller = get_controller(filename, self)
        self.filetree = FileTree(left_frame, self.controller.get_input_files(filename))

        with open(filename, "r") as f:
            self.code = TextView(frame, f.read(), width=80, height=30, wrap=NONE)

        self.proptree = PropertyTree(
            left_frame,
            self.controller.get_property_list(),
            self.controller.get_property_value,
        )

        self.filetree.bind("<ButtonRelease>", self.open_source_file)

        # Window layout
        self.code.grid(column=1, row=0, sticky=NSEW)
        self.console.grid(column=0, row=1, sticky=EW)
        self.filetree.grid(column=0, row=0, sticky=EW)
        self.proptree.grid(column=0, row=1, sticky=NS)
        left_frame.grid(column=0, row=0, sticky=NS)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        frame.grid(column=0, row=0, sticky=NSEW)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def open_source_file(self, filename: str) -> None:
        with open(os.path.join(self.root_dir, filename), "r") as f:
            self.code.new_content(f.read())

    @contextmanager
    def stdout_to_console(self):
        """Redirect stdout to the console"""
        original_stdout_fd = sys.stdout.fileno()
        libc = ctypes.CDLL(None)
        c_stdout = ctypes.c_void_p.in_dll(libc, "stdout")

        def _redirect_stdout(to_fd, mode):
            # Flush the C-level buffer stdout
            libc.fflush(c_stdout)
            # Flush and close sys.stdout - also closes the file descriptor (fd)
            sys.stdout.close()
            # Make original_stdout_fd point to the same file as to_fd
            os.dup2(to_fd, original_stdout_fd)
            # Create a new sys.stdout that points to the redirected fd
            sys.stdout = os.fdopen(original_stdout_fd, mode)

        saved_stdout_fd = os.dup(original_stdout_fd)
        try:
            # Create a pipe and redirect stdout to it
            r_fd, w_fd = os.pipe()
            _redirect_stdout(w_fd, "wb")
            # Yield to caller, then redirect stdout back to the saved fd
            yield
            os.close(w_fd)
            _redirect_stdout(saved_stdout_fd, "w")
            # Copy contents of pipe to the given stream
            f = os.fdopen(r_fd, "r")
            self.console.write(f.read())
        finally:
            os.close(saved_stdout_fd)


class App(tk.Tk):
    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.title(f"JSBSim {Controller.get_version()}")
        self.resizable(False, False)

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

    def open_script(self, filename: str) -> None:
        self.resizable(True, True)
        # Remove the logo
        self.main.destroy()

        # Open the file in an text widget
        script_relpath = os.path.relpath(filename, self.root_dir)
        self.title(f"JSBSim {Controller.get_version()} - {script_relpath}")
        self.main = SourceEditor(
            self, filename, self.root_dir, self.initialize_controller
        )
        self.main.grid(column=0, row=0, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def initialize_controller(self, script_name: str, widget: tk.Widget) -> Controller:
        self.controller = Controller(self.root_dir, widget)
        self.controller.load_script(script_name)
        return self.controller
