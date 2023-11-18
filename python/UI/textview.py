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

import tkinter as tk
from tkinter import ttk
from tkinter.constants import (
    DISABLED,
    END,
    EW,
    FLAT,
    HORIZONTAL,
    MOVETO,
    NONE,
    NORMAL,
    NS,
    NSEW,
    SUNKEN,
    VERTICAL,
)
from typing import Optional


class TextView(ttk.Frame):
    """Display text with scrollbar(s)"""

    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master)
        self.text = tk.Text(self, **kw)
        self.text.grid(column=0, row=0, sticky=NSEW)

        # Vertical scrollbar
        self.yscrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=self.text.yview)
        self.yscrollbar.grid(column=1, row=0, sticky=NS)
        self.text["yscrollcommand"] = self.yscrollbar.set

        # Horizontal scrollbar if the text is not wrapped
        if "wrap" in kw and kw["wrap"] == NONE:
            self.xscrollbar: Optional[ttk.Scrollbar] = ttk.Scrollbar(
                self, orient=HORIZONTAL, command=self.text.xview
            )
            self.xscrollbar.grid(column=0, row=1, sticky=EW)
            self.text["xscrollcommand"] = self.xscrollbar.set
        else:
            self.xscrollbar = None

        # Insert text
        if contents:
            self.text.insert("1.0", contents)

        # Widget layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def new_content(self, contents: str):
        self.text.delete("1.0", END)
        self.text.insert("1.0", contents)


class SourceCodeView(TextView):
    def __init__(self, master: tk.Widget, contents: str | None = None, **kw):
        super().__init__(master, contents, **kw)
        source_frame = ttk.Frame(self, relief=SUNKEN)
        source_frame.grid(column=0, row=0, sticky=NSEW)

        self.line_numbers = tk.Text(source_frame, width=3, bg="light gray", relief=FLAT)
        self.line_numbers.grid(column=0, row=0, sticky=NS)
        self.line_numbers["yscrollcommand"] = self.move_text

        self.text.destroy()
        self.text = tk.Text(source_frame, **kw)
        self.text.grid(column=1, row=0, sticky=NSEW)
        self.text["yscrollcommand"] = self.move_line_numbers
        self.text.configure(relief=FLAT)

        if self.xscrollbar:
            self.text["xscrollcommand"] = self.xscrollbar.set
            self.xscrollbar.config(command=self.text.xview)

        self.yscrollbar.config(command=self.yview)

        source_frame.grid_columnconfigure(1, weight=1)
        source_frame.grid_rowconfigure(0, weight=1)

        if contents:
            self.new_content(contents)

        self.line_numbers.bind("<Button-1>", self.goto_line)
        self.text.bind("<KeyRelease>", self.update_line_numbers)

    def move_text(self, first: float, last: float):
        self.yscrollbar.set(first, last)
        self.text.yview(MOVETO, first)

    def move_line_numbers(self, first: float, last: float):
        self.yscrollbar.set(first, last)
        self.line_numbers.yview(MOVETO, first)

    def yview(self, *args):
        self.text.yview(*args)
        self.line_numbers.yview(*args)

    def new_content(self, contents: str):
        super().new_content(contents)
        self.update_line_numbers(None)

    def goto_line(self, event: tk.Event):
        line = self.line_numbers.index(f"@{event.x},{event.y} linestart")
        self.text.see(f"{line}")

    def update_line_numbers(self, _):
        num_text_lines = int(self.text.index(END).split(".", maxsplit=1)[0])
        num_line_numbers = int(self.line_numbers.index(END).split(".", maxsplit=1)[0])-1
        self.line_numbers.configure(state=NORMAL)
        if num_text_lines < num_line_numbers:
            self.line_numbers.delete(f"{num_text_lines}.0", END)
            self.line_numbers.insert(END,"\n")
        elif num_text_lines > num_line_numbers:
            self.line_numbers.insert(
                END,
                "\n".join([str(i) for i in range(num_line_numbers, num_text_lines)])
                + "\n",
            )
        self.line_numbers.configure(state=DISABLED)


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
