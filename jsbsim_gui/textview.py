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

import tkinter as tk
from tkinter import ttk, TclError
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
from typing import Callable, List, Literal, Optional, Tuple, Union
from xml.parsers import expat

from pygments import lex
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Name, String, Text, _TokenType

from .edit_actions import REDO_SHORTCUT, SHORTCUT_MODIFIER, EditAction, EditableFrame


class TextView(EditableFrame):
    """Display text with scrollbar(s)"""

    def __init__(
        self,
        master: tk.Widget,
        contents: Optional[str] = None,
        frame_column: int = 0,
        **kw,
    ):
        super().__init__(master)
        self._text = tk.Text(self, **kw)
        self._text.grid(column=frame_column, row=0, sticky=NSEW)

        # Vertical scrollbar
        self._yscrollbar = ttk.Scrollbar(
            self, orient=VERTICAL, command=self._text.yview
        )
        self._yscrollbar.grid(column=frame_column + 1, row=0, sticky=NS)
        self._text["yscrollcommand"] = self._yscrollbar.set

        # Horizontal scrollbar if the text is not wrapped
        if "wrap" in kw and kw["wrap"] == NONE:
            self.xscrollbar: Optional[ttk.Scrollbar] = ttk.Scrollbar(
                self, orient=HORIZONTAL, command=self._text.xview
            )
            self.xscrollbar.grid(column=frame_column, row=1, sticky=EW)
            self._text["xscrollcommand"] = self.xscrollbar.set
        else:
            self.xscrollbar = None

        # Insert text
        if contents:
            self._text.insert("1.0", contents)

        # Widget layout
        self.grid_columnconfigure(frame_column, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._text.bind("<<Paste>>", lambda e: self._paste())
        self._text.bind(
            f"<{REDO_SHORTCUT}>", lambda e: self._on_edit_shortcut(EditAction.REDO)
        )
        self._text.bind(
            f"<{SHORTCUT_MODIFIER}-a>",
            lambda e: self._on_edit_shortcut(EditAction.SELECT_ALL),
        )

    def _on_edit_shortcut(self, action: EditAction) -> str:
        self.apply_edit_action(action)
        return "break"

    def _paste(self) -> str:
        try:
            clipboard_text = self._text.clipboard_get()
        except TclError:
            return "break"

        selection_bounds = self._text.tag_ranges(tk.SEL)
        if selection_bounds:
            start, end = selection_bounds
            self._text.config(autoseparators=False)
            self._text.edit_separator()
            self._text.delete(start, end)
            self._text.insert(start, clipboard_text)
            self._text.edit_separator()
            self._text.config(autoseparators=True)
        else:
            self._text.insert(tk.INSERT, clipboard_text)

        return "break"

    def new_content(self, contents: str) -> None:
        self._text.delete("1.0", END)
        self._text.insert("1.0", contents)
        self._text.edit_modified(False)

    def get_content(self) -> str:
        return self._text.get("1.0", "end-1c")

    def focus_text(self) -> None:
        self._text.focus_set()

    def move_cursor(self, position: str, focus: bool = True) -> None:
        self._text.mark_set(tk.INSERT, f"{position}")
        self._text.see(tk.INSERT)
        if focus:
            self.after_idle(self._text.focus_set)

    def select_text(self, text: str, position: str) -> None:
        self._text.tag_remove(tk.SEL, "1.0", tk.END)
        end_position = f"{position} + {len(text)} chars"
        self._text.tag_add(tk.SEL, position, end_position)
        self._text.mark_set(tk.INSERT, f"{position}")
        self._text.see(position)

    def apply_edit_action(self, action: EditAction) -> None:
        if action is EditAction.UNDO:
            try:
                self._text.edit_undo()
            except tk.TclError:
                pass
        elif action is EditAction.REDO:
            try:
                self._text.edit_redo()
            except tk.TclError:
                pass
        elif action is EditAction.SELECT_ALL:
            self._text.tag_add(tk.SEL, "1.0", "end-1c")
            self._text.mark_set(tk.INSERT, "1.0")
            self._text.see(tk.INSERT)
        elif action is EditAction.CUT:
            self._text.event_generate("<<Cut>>")
        elif action is EditAction.COPY:
            self._text.event_generate("<<Copy>>")
        elif action is EditAction.PASTE:
            self._paste()

    def bind(
        self,
        sequence: str,
        func: Callable[[tk.Event], str],
        add: Union[bool, Literal["", "+"], None] = None,
    ) -> str:
        return self._text.bind(sequence, func, add)


class SourceCodeView(TextView):
    """Display text with line numbers"""

    HIGHLIGHT_DELAY_MS = 300

    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        # Override parameters defined upstream
        kw["borderwidth"] = 0
        kw["relief"] = FLAT
        super().__init__(master, frame_column=1, undo=True, **kw)
        self._modified_text_callbacks: List[Callable[[bool], None]] = []
        self._highlight_timer: Optional[str] = None
        self._lexer: Optional[Lexer] = None

        self._line_numbers = tk.Text(
            self, width=1, bg="#eeeeee", borderwidth=0, relief=FLAT, wrap=NONE
        )
        # Even when empty, the first line is where the cursor is so we need a number
        self._line_numbers.insert("1.0", "1")
        self._line_numbers.grid(column=0, row=0, sticky=NS)
        self._line_numbers.bind("<Button-1>", self._goto_line)
        self._line_numbers.bind("<MouseWheel>", self._on_line_numbers_scroll)
        self._line_numbers.bind("<Button-4>", self._on_line_numbers_scroll)
        self._line_numbers.bind("<Button-5>", self._on_line_numbers_scroll)
        self._line_numbers.configure(state=DISABLED)

        self._text["yscrollcommand"] = self._move_line_numbers
        self._yscrollbar.configure(command=self._yview)
        self._modified_event_id = self._text.bind(
            "<<Modified>>", self._on_text_modified
        )

        if contents:
            self.new_content(contents)

    def bind_modified_text(
        self, func: Callable[[bool], None], add: bool = False
    ) -> None:
        if add:
            self._modified_text_callbacks.append(func)
        else:
            self._modified_text_callbacks = [func]

    def _on_text_modified(self, _event: tk.Event) -> None:
        modified = self._text.edit_modified()
        for func in self._modified_text_callbacks:
            func(modified)

        self._update_line_numbers()

        if self._highlight_timer:
            self.after_cancel(self._highlight_timer)
        self._highlight_timer = self.after(
            self.HIGHLIGHT_DELAY_MS, self._update_highlighting
        )

        self._text.edit_modified(False)

    def _update_highlighting(self) -> None:
        self._highlight_timer = None
        if self._lexer:
            self.highlight_text()

    def highlight_text(self) -> None:
        if not self._lexer:
            return

        content = self.get_content()
        for tag in self._get_highlight_tags():
            self._text.tag_remove(tag, "1.0", END)

        line, col = 1, 0
        for token, value in lex(content, self._lexer):
            if not value:
                continue

            start = f"{line}.{col}"
            segments = value.split("\n")
            num_newlines = len(segments) - 1

            if num_newlines > 0:
                line += num_newlines
                col = len(segments[-1])
            else:
                col += len(value)

            end = f"{line}.{col}"
            tag_name = self._get_tag_name(token)
            if tag_name:
                self._text.tag_add(tag_name, start, end)

    def _get_highlight_tags(self) -> List[str]:
        return []

    def _get_tag_name(self, _token: _TokenType) -> Optional[str]:
        return None

    def _move_line_numbers(self, first: float, last: float) -> None:
        self._yscrollbar.set(first, last)
        self._line_numbers.yview(MOVETO, first)

    def _yview(self, *args) -> None:
        self._line_numbers.yview(*args)
        self._text.yview(*args)

    def new_content(self, contents: str) -> None:
        # Avoid calling `self.on_text_modified` as new content will be loaded in the editor.
        self._text.unbind("<<Modified>>", self._modified_event_id)
        super().new_content(contents)
        self._update_line_numbers()
        self._modified_event_id = self._text.bind(
            "<<Modified>>", self._on_text_modified
        )

    def _goto_line(self, event: tk.Event) -> None:
        position = self._line_numbers.index(f"@{event.x},{event.y} linestart")
        self.move_cursor(position)

    def _on_line_numbers_scroll(self, event: tk.Event) -> str:
        if event.num == 4 or event.delta > 0:
            self._text.yview_scroll(-3, "units")
        elif event.num == 5 or event.delta < 0:
            self._text.yview_scroll(3, "units")

        return "break"

    def _update_line_numbers(self) -> None:
        num_text_lines = int(self._text.index(END).split(".", maxsplit=1)[0])
        num_line_numbers = int(self._line_numbers.index(END).split(".", maxsplit=1)[0])
        self._line_numbers.configure(state=NORMAL)

        # Adjust the width of the line numbers widget based on the number of digits
        # required to display the last line number
        required_width = len(str(num_text_lines))
        current_width = int(self._line_numbers.cget("width"))
        if required_width != current_width:
            self._line_numbers.configure(width=required_width)
            # Adjust the text widget so that the cumulated width of the line numbers
            # widget and the text widget is constant. This is to avoid display glitches.
            text_width = int(self._text.cget("width"))
            text_width -= required_width - current_width
            self._text.configure(width=text_width)
            # Empty the line numbers widget because we are modifying the text layout.
            num_line_numbers = 1
            self._line_numbers.delete("1.0", END)

        if num_text_lines < num_line_numbers:
            self._line_numbers.delete(f"{num_text_lines}.0", END)
        elif num_text_lines > num_line_numbers:
            if num_line_numbers > 1:
                self._line_numbers.insert(END, "\n")
            self._line_numbers.insert(
                END,
                "\n".join(
                    [
                        str(i).rjust(required_width)
                        for i in range(num_line_numbers, num_text_lines)
                    ]
                ),
            )
        self._line_numbers.configure(state=DISABLED)


class XMLSourceCodeView(SourceCodeView):
    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master, contents, **kw)

        self._text.tag_configure("XML_tag", foreground="#ff00ff")
        self._text.tag_configure("XML_comment", foreground="#00aaaa")
        self._text.tag_configure("XML_attr_name", foreground="#00aa00")
        self._text.tag_configure("XML_attr_value", foreground="#aaaa00")
        self._text.tag_configure("XML_data", foreground="#000000")

        self._lexer = get_lexer_by_name("xml")
        self._parser = self.new_parser()
        if contents:
            self._parser.Parse(contents)
            self.highlight_text()

    def _get_highlight_tags(self) -> List[str]:
        return ["XML_tag", "XML_comment", "XML_attr_name", "XML_attr_value", "XML_data"]

    def _get_tag_name(self, token: _TokenType) -> Optional[str]:
        if token in Name.Tag:
            return "XML_tag"
        if token in Comment:
            return "XML_comment"
        if token in Name.Attribute:
            return "XML_attr_name"
        if token in String:
            return "XML_attr_value"
        if token in Text:
            return "XML_data"
        return None

    def new_parser(self) -> expat.XMLParserType:
        parser = expat.ParserCreate()
        parser.buffer_text = True
        return parser

    def new_content(self, contents: str) -> None:
        super().new_content(contents)
        self._parser = self.new_parser()
        try:
            self._parser.Parse(contents)
        except expat.ExpatError:
            pass
        self.highlight_text()

    def extract_tagged_regions(self, tag_name: str) -> List[Tuple[int, int, str]]:
        tagged_regions = []
        ranges = self._text.tag_ranges(tag_name)
        for i in range(0, len(ranges), 2):
            start_index = str(ranges[i])
            end_index = str(ranges[i + 1])

            line, column = map(int, start_index.split("."))
            text = self._text.get(start_index, end_index)
            tagged_regions.append((line, column, text))

        return tagged_regions
