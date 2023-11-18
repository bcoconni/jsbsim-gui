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
from tkinter import ttk
from tkinter.constants import EW, NONE, NS, NSEW
from typing import Callable

from .controller import Controller
from .hierarchical_tree import FileTree, PropertyTree
from .textview import Console, XMLSourceCodeView


class LabeledWidget(ttk.Frame):
    def __init__(self, master: tk.Widget, label: str):
        super().__init__(master)
        self.widget: tk.Widget | None = None
        self.label = ttk.Label(self, text=label)
        self.label.grid(column=0, row=0)

    def set_widget(self, widget: tk.Widget) -> None:
        self.widget = widget
        self.widget.grid(column=0, row=1, sticky=NSEW)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def set_label(self, label: str) -> None:
        self.label.config(text=label)


class SourceEditor(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        filename: str,
        root_dir: str,
        get_controller: Callable[[str, tk.Widget], Controller],
    ):
        super().__init__(master)
        self.root_dir = root_dir
        main_frame = ttk.Frame(self)
        left_frame = ttk.Frame(main_frame)

        self.console = Console(self, height=10)
        controller = get_controller(filename, self)
        fileview = LabeledWidget(left_frame, "Project Files")
        fileview.set_widget(FileTree(fileview, controller.get_input_files(filename)))

        with open(filename, "r") as f:
            file_relpath = os.path.relpath(filename, self.root_dir)
            self.codeview = LabeledWidget(main_frame, file_relpath)
            self.codeview.set_widget(
                XMLSourceCodeView(
                    self.codeview, f.read(), width=80, height=30, wrap=NONE
                )
            )

        property_view = LabeledWidget(left_frame, "Property List")
        property_view.set_widget(
            PropertyTree(
                property_view,
                controller.get_property_list(),
                controller.get_property_value,
            )
        )

        fileview.widget.bind("<ButtonRelease>", self.open_source_file)

        # Window layout
        self.codeview.grid(column=1, row=0, sticky=NSEW)
        self.console.grid(column=0, row=1, sticky=EW)
        fileview.grid(column=0, row=0, sticky=EW)
        property_view.grid(column=0, row=1, sticky=NS)
        left_frame.grid(column=0, row=0, sticky=NS)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid(column=0, row=0, sticky=NSEW)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def open_source_file(self, filename: str) -> None:
        editor = self.codeview.widget
        if editor:
            with open(os.path.join(self.root_dir, filename), "r") as f:
                self.codeview.set_label(filename)
                editor.new_content(f.read())

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
