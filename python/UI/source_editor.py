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
from tkinter import ttk
from tkinter.constants import EW, NONE, NS, NSEW

from .controller import Controller
from .hierarchical_tree import FileTree, PropertyTree
from .textview import XMLSourceCodeView


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
        controller: Controller,
        filename: str,
        root_dir: str,
    ):
        super().__init__(master)
        self.root_dir = root_dir
        main_frame = ttk.Frame(self)
        left_frame = ttk.Frame(main_frame)

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
            PropertyTree(property_view, controller.get_property_list())
        )

        fileview.widget.bind_selection(self.open_source_file)

        # Window layout
        self.codeview.grid(column=1, row=0, sticky=NSEW)
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
