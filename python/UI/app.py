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
from tkinter.constants import *
from tkinter.messagebox import showerror
from typing import Optional, Callable

from PIL import Image, ImageTk

from .controller import Controller


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


class TextView(ttk.Frame):
    """Display text with scrollbar(s)"""

    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master)
        self.text = tk.Text(self, **kw)
        self.text.grid(column=0, row=0, sticky=NSEW)

        # Vertical scrollbar
        ys = ttk.Scrollbar(self, orient=VERTICAL, command=self.text.yview)
        ys.grid(column=1, row=0, sticky=NS)
        self.text["yscrollcommand"] = ys.set

        # Horizontal scrollbar if the text is not wrapped
        if "wrap" in kw and kw["wrap"] == NONE:
            xs = ttk.Scrollbar(self, orient=HORIZONTAL, command=self.text.xview)
            xs.grid(column=0, row=1, sticky=EW)
            self.text["xscrollcommand"] = xs.set

        # Insert text
        if contents:
            self.text.insert("1.0", contents)

        # Widget layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)


class Console(TextView):
    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master, contents, **kw)
        # Set the text to read only
        self.text.configure(state=DISABLED)

    def write(self, contents: str):
        self.text.configure(state=NORMAL)
        self.text.insert(END, contents)
        self.text.see(END)
        self.text.configure(state=DISABLED)


class HierarchicalList(ttk.Treeview):
    def __init__(
        self,
        master: tk.Widget,
        elements: list[str],
        columns_id: tuple[str],
        columns_name: tuple[str],
        is_open: bool = True,
    ):
        super().__init__(master, columns=columns_id)

        for cid, name in zip(columns_id, columns_name):
            self.heading(cid, text=name, anchor=tk.W)
        self.column("#0", width=60, stretch=False)

        self.leafs = {}

        for elm in sorted(elements):
            node = ""
            for name in elm.split("/"):
                parent = node
                node = "/".join((parent, name))
                if node in self.leafs:
                    continue

                display_name = "  " * parent.count("/") + name
                if parent:
                    piid = self.leafs[parent]
                else:
                    piid = ""
                self.leafs[node] = self.insert(
                    piid, tk.END, values=(display_name, ""), open=is_open
                )


class PropertyList(HierarchicalList):
    def __init__(
        self,
        master: tk.Widget,
        properties: list[str],
        get_property_value: Callable[[str], float],
    ):
        super().__init__(master, properties, ("prop", "val"), ("Name", "Values"), False)

        for p in sorted(properties):
            self.set(self.leafs["/" + p], "val", get_property_value(p))


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
        frame = ttk.Frame(self)
        left_frame = ttk.Frame(frame)

        # Open the file in an text widget
        script_relpath = os.path.relpath(filename, self.root_dir)
        with open(filename, "r") as f:
            self.title(f"JSBSim {Controller.get_version()} - {script_relpath}")
            self.code = TextView(
                frame, "".join(f.readlines()), width=80, height=30, wrap=NONE
            )

        self.console = Console(self, height=10)

        self.controller = Controller(self.root_dir, self)
        file_list = self.controller.load_script(script_relpath)

        file_list.append(script_relpath)
        self.filelist = HierarchicalList(left_frame, file_list, ("name",), ("Name",))

        self.proplist = PropertyList(
            left_frame,
            self.controller.get_property_list(),
            self.controller.get_property_value,
        )

        # Window layout
        self.code.grid(column=1, row=0, sticky=NSEW)
        self.console.grid(column=0, row=1, sticky=EW)
        self.filelist.grid(column=0, row=0, sticky=EW)
        self.proplist.grid(column=0, row=1, sticky=NS)
        left_frame.grid(column=0, row=0, sticky=NS)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        frame.grid(column=0, row=0, sticky=NSEW)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

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
