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
from tkinter.messagebox import showerror
from typing import Optional

from jsbsim.UI.controller import Controller
from PIL import Image, ImageTk


class MenuBar(tk.Menu):
    def __init__(self, root: tk.Widget, root_dir: str):
        super().__init__(root)
        self.root_dir = root_dir

        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="Open...", command=self.select_script_file)
        file_menu.add_command(label="Exit", command=root.destroy)
        self.add_cascade(label="File", menu=file_menu)

    def select_script_file(self) -> None:
        filename = fd.askopenfilename(
            title="Open a script",
            initialdir=self.root_dir,
            filetypes=(("script files", "*.xml"),),
        )
        if filename:
            self.master.open_script(filename)


class Text(ttk.Frame):
    def __init__(self, root: tk.Widget, text: Optional[str] = None, **kw):
        super().__init__(root)
        self.text = tk.Text(self, **kw)
        self.text.grid(column=0, row=0, sticky="nwes")

        # Vertical scrollbar
        ys = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        ys.grid(column=1, row=0, sticky="ns")
        self.text["yscrollcommand"] = ys.set

        # Horizontal scrollbar if the text is not wrapped
        if "wrap" in kw and kw["wrap"] == "none":
            xs = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
            xs.grid(column=0, row=1, sticky="we")
            self.text["xscrollcommand"] = xs.set

        # Insert text
        if text:
            self.text.insert("1.0", text)

        # Widget layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)


class Console(Text):
    def __init__(self, root: tk.Widget, text: Optional[str] = None, **kw):
        super().__init__(root, text, **kw)
        # Set the text to read only
        self.text["state"] = "disabled"

    def write(self, text: str):
        self.text["state"] = "normal"
        self.text.insert("end", text)
        self.text.see("end")
        self.text["state"] = "disabled"


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
            self.logo = ttk.Label(self, image=logo_image, background="white")
            self.logo.image = logo_image
            self.logo.grid(padx=(600 - logo_resized.width) // 2)

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
        self.logo.destroy()

        # Open the file in an text widget
        relpath = os.path.relpath(filename, self.root_dir)
        with open(filename, "r") as f:
            self.title(f"JSBSim {Controller.get_version()} - {relpath}")
            self.code = Text(
                self, "".join(f.readlines()), width=80, height=30, wrap="none"
            )

        self.code.grid(column=0, row=0, sticky="nwes")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.console = Console(self, height=10)
        self.console.grid(column=0, row=1, sticky="we")

        self.controller = Controller(self.root_dir, self)

    @contextmanager
    def stdout_to_console(self):
        """Redirect stdout to the console"""
        original_stdout_fd = sys.stdout.fileno()
        libc = ctypes.CDLL(None)
        c_stdout = ctypes.c_void_p.in_dll(libc, "stdout")

        def _redirect_stdout(to_fd):
            # Flush the C-level buffer stdout
            libc.fflush(c_stdout)
            # Flush and close sys.stdout - also closes the file descriptor (fd)
            sys.stdout.close()
            # Make original_stdout_fd point to the same file as to_fd
            os.dup2(to_fd, original_stdout_fd)
            # Create a new sys.stdout that points to the redirected fd
            sys.stdout = os.fdopen(original_stdout_fd, "wb")

        saved_stdout_fd = os.dup(original_stdout_fd)
        try:
            # Create a pipe and redirect stdout to it
            r_fd, w_fd = os.pipe()
            _redirect_stdout(w_fd)
            # Yield to caller, then redirect stdout back to the saved fd
            yield
            os.close(w_fd)
            _redirect_stdout(saved_stdout_fd)
            # Copy contents of pipe to the given stream
            f = os.fdopen(r_fd, "r")
            self.console.write(f.read())
        finally:
            os.close(saved_stdout_fd)
