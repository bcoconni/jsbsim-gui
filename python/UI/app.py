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

import io
import os
import sys
import tempfile
import tkinter as tk
import xml.etree.ElementTree as et
from contextlib import contextmanager
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter.constants import EW, NSEW
from tkinter.messagebox import showerror
from typing import Callable, Optional

from PIL import Image, ImageTk

from .controller import Controller
from .run import Run
from .source_editor import SourceEditor
from .textview import Console


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
                use_el = root.find("use")
                aircraft_name = use_el.attrib["aircraft"]
                self.master.open_file(filename, aircraft_name, Controller.load_script)
            elif root.tag == "fdm_config":
                aircraft_name = os.path.splitext(os.path.basename(filename))[0]
                self.master.open_file(filename, aircraft_name, Controller.load_aircraft)
            else:
                name = os.path.relpath(filename, self.root_dir)
                showerror(
                    "Error",
                    message=f'The file "{name}" is neither a JSBSim script nor an aircraft',
                )
                return

        view_menu = tk.Menu(self, tearoff=False)
        view_menu.add_command(label="Edit", command=self.master.edit)
        view_menu.add_command(label="Run", command=self.master.run)
        self.add_cascade(label="View", menu=view_menu)


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

        self.console: Console | None = None
        self._controller: Controller | None = None
        self.filename: str | None = None

    def run(self) -> None:
        w = self.main.winfo_width()
        h = self.main.winfo_height()
        self.main.destroy()
        self.main = Run(self, self._controller, width=w, height=h)
        self.main.grid_propagate(0)

        # Window layout
        self.main.grid(column=0, row=0, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def edit(self) -> None:
        self.main.destroy()

        # Open the file in a text widget
        self.main = SourceEditor(self, self._controller, self.filename, self.root_dir)

        # Window layout
        self.main.grid(column=0, row=0, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def open_file(
        self,
        filename: str,
        aircraft_name: str,
        load_file: Callable[[Controller, str], None],
    ) -> None:
        self.resizable(True, True)
        # Remove the logo
        self.title(f"JSBSim {Controller.get_version()} - {aircraft_name}")

        if not self.console:
            self.console = Console(self, height=10)
            self.console.grid(column=0, row=1, sticky=EW)

        self._controller = Controller(self.root_dir, self)
        load_file(self._controller, filename)
        self.filename = filename
        self.edit()

    @contextmanager
    def stdout_to_console(self):
        """Redirect stdout to the console"""
        original_stdout_fd = sys.stdout.fileno()

        def _redirect_stdout(to_fd):
            # Flush and close sys.stdout - also closes the file descriptor (fd)
            sys.stdout.close()
            # Make original_stdout_fd point to the same file as to_fd
            os.dup2(to_fd, original_stdout_fd)
            # Create a new sys.stdout that points to the redirected fd
            sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, "wb"))

        saved_stdout_fd = os.dup(original_stdout_fd)
        try:
            # Create a temporary file and redirect stdout to it
            tfile = tempfile.TemporaryFile(mode="w+b")
            _redirect_stdout(tfile.fileno())
            # Yield to caller, then redirect stdout back to the saved fd
            yield
            _redirect_stdout(saved_stdout_fd)
            # Copy contents of temporary file to the given stream
            tfile.flush()
            tfile.seek(0, io.SEEK_SET)
            self.console.write(tfile.read())
        finally:
            os.close(saved_stdout_fd)
