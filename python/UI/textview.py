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
    HORIZONTAL,
    NONE,
    NORMAL,
    NS,
    NSEW,
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

    def new_content(self, contents):
        self.text.delete("1.0", END)
        self.text.insert("1.0", contents)

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
