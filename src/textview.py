# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2026 Bertrand Coconnier
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
from contextlib import contextmanager
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
    VERTICAL,
)
from typing import Callable, Dict, List, Optional, Tuple
from xml.parsers import expat


class TextView(ttk.Frame):
    """Display text with scrollbar(s)"""

    def __init__(
        self,
        master: tk.Widget,
        contents: Optional[str] = None,
        frame_column: int = 0,
        **kw,
    ):
        super().__init__(master)
        self.text = tk.Text(self, **kw)
        self.text.grid(column=frame_column, row=0, sticky=NSEW)

        # Vertical scrollbar
        self.yscrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=self.text.yview)
        self.yscrollbar.grid(column=frame_column + 1, row=0, sticky=NS)
        self.text["yscrollcommand"] = self.yscrollbar.set

        # Horizontal scrollbar if the text is not wrapped
        if "wrap" in kw and kw["wrap"] == NONE:
            self.xscrollbar: Optional[ttk.Scrollbar] = ttk.Scrollbar(
                self, orient=HORIZONTAL, command=self.text.xview
            )
            self.xscrollbar.grid(column=frame_column, row=1, sticky=EW)
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
        self.text.edit_modified(False)


class SourceCodeView(TextView):
    """Display text with line numbers"""

    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        # Override parameters defined upstream
        kw["borderwidth"] = 0
        kw["relief"] = FLAT
        super().__init__(master, frame_column=1, **kw)
        self.modified_text_callbacks: List[Callable[[bool], None]] = []

        self.line_numbers = tk.Text(
            self, width=1, bg="#eeeeee", borderwidth=0, relief=FLAT, wrap=NONE
        )
        # Even when empty, the first line is where the cursor is so we need a number
        self.line_numbers.insert("1.0", "1")
        self.line_numbers.grid(column=0, row=0, sticky=NS)
        self.line_numbers.bind("<Button-1>", self.goto_line)
        self.line_numbers.bind("<MouseWheel>", self.on_line_numbers_scroll)
        self.line_numbers.bind("<Button-4>", self.on_line_numbers_scroll)
        self.line_numbers.bind("<Button-5>", self.on_line_numbers_scroll)
        self.line_numbers.configure(state=DISABLED)

        self.text["yscrollcommand"] = self.move_line_numbers
        self.yscrollbar.configure(command=self.yview)
        self.modified_event_id = self.text.bind("<<Modified>>", self.on_text_modified)

        if contents:
            self.new_content(contents)

    def bind_modified_text(
        self, func: Callable[[bool], None], add: bool = False
    ) -> None:
        if add:
            self.modified_text_callbacks.append(func)
        else:
            self.modified_text_callbacks = [func]

    def on_text_modified(self, _event: tk.Event) -> None:
        modified = self.text.edit_modified()
        for func in self.modified_text_callbacks:
            func(modified)

        self.update_line_numbers()
        self.text.edit_modified(False)

    def move_line_numbers(self, first: float, last: float) -> None:
        self.yscrollbar.set(first, last)
        self.line_numbers.yview(MOVETO, first)

    def yview(self, *args) -> None:
        self.line_numbers.yview(*args)
        self.text.yview(*args)

    def new_content(self, contents: str) -> None:
        # Avoid calling `self.on_text_modified` as new content will be loaded in the editor.
        self.text.unbind("<<Modified>>", self.modified_event_id)
        super().new_content(contents)
        self.update_line_numbers()
        self.modified_event_id = self.text.bind("<<Modified>>", self.on_text_modified)

    def goto_line(self, event: tk.Event) -> None:
        position = self.line_numbers.index(f"@{event.x},{event.y} linestart")
        self.text.mark_set(tk.INSERT, f"{position}")
        self.text.see(tk.INSERT)
        self.text.focus()

    def on_line_numbers_scroll(self, event: tk.Event) -> str:
        if event.num == 4 or event.delta > 0:
            self.text.yview_scroll(-3, "units")
        elif event.num == 5 or event.delta < 0:
            self.text.yview_scroll(3, "units")

        return "break"

    def update_line_numbers(self) -> None:
        num_text_lines = int(self.text.index(END).split(".", maxsplit=1)[0])
        num_line_numbers = int(self.line_numbers.index(END).split(".", maxsplit=1)[0])
        self.line_numbers.configure(state=NORMAL)

        # Adjust the width of the line numbers widget based on the number of digits
        # required to display the last line number
        required_width = len(str(num_text_lines))
        current_width = int(self.line_numbers.cget("width"))
        if required_width != current_width:
            self.line_numbers.configure(width=required_width)
            # Adjust the text widget so that the cumulated width of the line numbers
            # widget and the text widget is constant. This is to avoid display glitches.
            text_width = int(self.text.cget("width"))
            text_width -= required_width - current_width
            self.text.configure(width=text_width)
            # Empty the line numbers widget because we are modifying the text layout.
            num_line_numbers = 1
            self.line_numbers.delete("1.0", END)

        if num_text_lines < num_line_numbers:
            self.line_numbers.delete(f"{num_text_lines}.0", END)
        elif num_text_lines > num_line_numbers:
            if num_line_numbers > 1:
                self.line_numbers.insert(END, "\n")
            self.line_numbers.insert(
                END,
                "\n".join(
                    [
                        str(i).rjust(required_width)
                        for i in range(num_line_numbers, num_text_lines)
                    ]
                ),
            )
        self.line_numbers.configure(state=DISABLED)


class XMLSourceCodeView(SourceCodeView):
    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master, contents, **kw)

        self.text.tag_configure("XML_tag", foreground="#ff00ff")
        self.text.tag_configure("XML_comment", foreground="#00aaaa")
        self.text.tag_configure("XML_attr_name", foreground="#00aa00")
        self.text.tag_configure("XML_attr_value", foreground="#aaaa00")
        self.text.tag_configure("XML_data", foreground="#000000")

        self.parser = self.new_parser()
        if contents:
            self.parser.Parse(contents)

    def new_parser(self) -> expat.XMLParserType:
        parser = expat.ParserCreate()
        parser.buffer_text = True
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CommentHandler = self.comments
        parser.XmlDeclHandler = self.xmldecl
        parser.DefaultHandler = self.character_data
        return parser

    def start_element(self, name: str, attrs: Dict[str, str]) -> None:
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

    def _get_multilines_start_end(self, data: str) -> Tuple[int, int, int, int]:
        line1 = self.parser.CurrentLineNumber
        start = self.parser.CurrentColumnNumber
        data_lines = data.split("\n")
        nlines = len(data_lines)
        end = len(data_lines[-1])
        if nlines > 1:
            line2 = line1 + nlines - 1
        else:
            line2 = line1
            end += start
        return start, line1, end, line2

    def comments(self, data: str) -> None:
        start, line1, end, line2 = self._get_multilines_start_end(data)
        if line1 == line2:
            end += 7  # len("<!--") + len("-->") == 7
        else:
            end += 3  # len("-->") == 3
        self.text.tag_add("XML_comment", f"{line1}.{start}", f"{line2}.{end}")

    def xmldecl(self, version: str, encoding: Optional[str], _: int) -> None:
        attrs = {"version": version}
        if encoding:
            attrs["encoding"] = encoding
        self.start_element("?xml", attrs)

    def character_data(self, data: str) -> None:
        start, line1, end, line2 = self._get_multilines_start_end(data)
        self.text.tag_add("XML_data", f"{line1}.{start}", f"{line2}.{end}")

    def new_content(self, contents: str) -> None:
        super().new_content(contents)
        self.parser = self.new_parser()
        try:
            self.parser.Parse(contents)
        except expat.ExpatError:
            pass

    def extract_tagged_regions(self, tag_name: str) -> List[Tuple[int, int, str]]:
        tagged_regions = []
        ranges = self.text.tag_ranges(tag_name)
        for i in range(0, len(ranges), 2):
            start_index = str(ranges[i])
            end_index = str(ranges[i + 1])

            line, column = map(int, start_index.split("."))
            text = self.text.get(start_index, end_index)
            tagged_regions.append((line, column, text))

        return tagged_regions


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


# A class inheriting from console and redirecting stdout and stderr to the console
class ConsoleStdoutRedirect(Console):
    @contextmanager
    def redirect_stdout(self):
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
            self.write(tfile.read())
        finally:
            os.close(saved_stdout_fd)
