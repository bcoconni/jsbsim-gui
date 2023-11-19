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
from xml.parsers import expat


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

    def new_content(self, contents: str) -> None:
        self.text.delete("1.0", END)
        self.text.insert("1.0", contents)


class SourceCodeView(TextView):
    """Display text with line numbers"""

    def __init__(self, master: tk.Widget, contents: str | None = None, **kw):
        super().__init__(master, contents, **kw)
        source_frame = ttk.Frame(self, borderwidth=1, relief=SUNKEN)
        source_frame.grid(column=0, row=0, sticky=NSEW)

        self.line_numbers = tk.Text(
            source_frame, width=3, bg="#eeeeee", borderwidth=0, relief=FLAT
        )
        self.line_numbers.grid(column=0, row=0, sticky=NS)
        self.line_numbers["yscrollcommand"] = self.move_text

        self.text.destroy()
        self.text = tk.Text(source_frame, borderwidth=0, **kw)
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
            SourceCodeView.new_content(self, contents)

        self.line_numbers.bind("<Button-1>", self.goto_line)
        self.text.bind("<KeyRelease>", self.update_line_numbers)

    def move_text(self, first: float, last: float) -> None:
        self.yscrollbar.set(first, last)
        self.text.yview(MOVETO, first)

    def move_line_numbers(self, first: float, last: float) -> None:
        self.yscrollbar.set(first, last)
        self.line_numbers.yview(MOVETO, first)

    def yview(self, *args) -> tuple[float, float]:
        self.text.yview(*args)
        return self.line_numbers.yview(*args)

    def new_content(self, contents: str) -> None:
        super().new_content(contents)
        self.update_line_numbers(None)

    def goto_line(self, event: tk.Event) -> None:
        line = self.line_numbers.index(f"@{event.x},{event.y} linestart")
        self.text.see(f"{line}")

    def update_line_numbers(self, _) -> None:
        num_text_lines = int(self.text.index(END).split(".", maxsplit=1)[0])
        num_line_numbers = (
            int(self.line_numbers.index(END).split(".", maxsplit=1)[0]) - 1
        )
        self.line_numbers.configure(state=NORMAL)
        if num_text_lines < num_line_numbers:
            self.line_numbers.delete(f"{num_text_lines}.0", END)
            self.line_numbers.insert(END, "\n")
        elif num_text_lines > num_line_numbers:
            self.line_numbers.insert(
                END,
                "\n".join([str(i) for i in range(num_line_numbers, num_text_lines)])
                + "\n",
            )
        self.line_numbers.configure(state=DISABLED)


class XMLSourceCodeView(SourceCodeView):
    def __init__(self, master: tk.Widget, contents: str | None = None, **kw):
        super().__init__(master, contents, **kw)

        self.text.tag_configure("XML_tag", foreground="#ff00ff")
        self.text.tag_configure("XML_comment", foreground="#00aaaa")
        self.text.tag_configure("XML_attr_name", foreground="#00aa00")
        self.text.tag_configure("XML_attr_value", foreground="#aaaa00")

        self.parser = self.new_parser()
        if contents:
            self.parser.Parse(contents)

    def new_parser(self) -> expat.XMLParserType:
        parser = expat.ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CommentHandler = self.comments
        parser.XmlDeclHandler = self.xmldecl
        return parser

    def start_element(self, name: str, attrs: dict[str, str]) -> None:
        line = self.parser.CurrentLineNumber
        start = self.parser.CurrentColumnNumber + 1
        end = start + len(name)
        self.text.tag_add("XML_tag", f"{line}.{start}", f"{line}.{end}")

        if attrs:
            for attr_name, attr_value in attrs.items():
                index = self.text.search(attr_name, f"{line}.{end+1}")
                line, start = index.split(".")
                end = int(start) + len(attr_name)
                self.text.tag_add("XML_attr_name", index, f"{line}.{end}")

                index = self.text.search(attr_value, f"{line}.{end+1}")
                line, col = index.split(".")
                start = int(col)
                end = start + len(attr_value) + 1
                self.text.tag_add(
                    "XML_attr_value", f"{line}.{start-1}", f"{line}.{end}"
                )

    def end_element(self, name: str) -> None:
        line = self.parser.CurrentLineNumber
        start = self.parser.CurrentColumnNumber + 2
        end = start + len(name)
        self.text.tag_add("XML_tag", f"{line}.{start}", f"{line}.{end}")

    def comments(self, data: str) -> None:
        data_lines = data.split("\n")
        line1 = self.parser.CurrentLineNumber
        start = self.parser.CurrentColumnNumber
        comment_lines = len(data_lines)
        if comment_lines > 1:
            line2 = line1 + comment_lines - 1
            end = len(data_lines[-1]) + 3  # len("-->") == 3
        else:
            line2 = line1
            end = start + len(data_lines[-1]) + 7  # len("<!--") + len("-->") == 7
        self.text.tag_add("XML_comment", f"{line1}.{start}", f"{line2}.{end}")

    def xmldecl(self, version: str, encoding: str | None, standalone: int) -> None:
        attrs = {"version": version}
        if encoding:
            attrs["encoding"] = encoding
        self.start_element("?xml", attrs)

    def new_content(self, contents: str) -> None:
        super().new_content(contents)
        self.parser = self.new_parser()
        self.parser.Parse(contents)


class Console(TextView):
    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master, contents, **kw)
        # Set the text to read only
        self.text.configure(state=DISABLED)

    def write(self, contents: str) -> None:
        self.text.configure(state=NORMAL)
        self.text.insert(END, contents)
        self.text.see(END)
        self.text.configure(state=DISABLED)
