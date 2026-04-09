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
import tkinter.font as tkfont
from tkinter import ttk
from tkinter.constants import DISABLED, END, NORMAL
from typing import Callable, FrozenSet, List, Optional, Protocol, Tuple

from jsbsim import FGLogger, LogFormat, LogLevel

from .textview import TextView


class ConsoleWriter(Protocol):
    def write(self, contents: str) -> None: ...
    def write_formatted(self, segments: List[Tuple[str, FrozenSet[str]]]) -> None: ...


class ConsoleLogger(FGLogger):
    def __init__(
        self,
        output_console: ConsoleWriter,
        problems_console: ConsoleWriter,
        get_file_relative_path: Callable[[str], str],
    ):
        super().__init__()
        self._output_console = output_console
        self._problems_console = problems_console
        self._get_file_relative_path = get_file_relative_path
        self._segments: List[Tuple[str, FrozenSet[str]]] = []
        self._active_color: Optional[str] = None
        self._active_bold: bool = False
        self._active_underline: bool = False

    def set_level(self, level: LogLevel) -> None:
        super().set_level(level)
        self._segments.clear()
        if level in (LogLevel.WARN, LogLevel.ERROR, LogLevel.FATAL):
            self._active_color = "log_red"
            self._active_bold = True
            if level == LogLevel.WARN:
                self._active_color = "log_cyan"
                self.message("WARNING: ")
            elif level == LogLevel.ERROR:
                self.message("ERROR: ")
            else:
                self.message("FATAL: ")

        self._active_color = None
        self._active_bold = False
        self._active_underline = False

    def file_location(self, filename: str, line: int) -> None:
        underline = self._active_underline
        self._active_underline = True
        self.message(f"In {self._get_file_relative_path(filename)}: line {line}\n")
        self._active_underline = underline

    def message(self, text: str) -> None:
        tags = set()
        if self._active_color:
            tags.add(self._active_color)
        if self._active_bold:
            tags.add("log_bold")
        if self._active_underline:
            tags.add("log_underline")
        tags = frozenset(tags)

        if self._segments:
            prev_text, prev_tags = self._segments[-1]
            if tags == prev_tags:
                self._segments[-1] = (prev_text + text, prev_tags)
                return

        self._segments.append((text, tags))

    def format(self, fmt: LogFormat) -> None:
        if fmt == LogFormat.RESET:
            self._active_color = None
            self._active_bold = False
            self._active_underline = False
        elif fmt == LogFormat.BOLD:
            self._active_bold = True
        elif fmt == LogFormat.NORMAL:
            self._active_bold = False
        elif fmt == LogFormat.UNDERLINE_ON:
            self._active_underline = True
        elif fmt == LogFormat.UNDERLINE_OFF:
            self._active_underline = False
        elif fmt == LogFormat.RED:
            self._active_color = "log_red"
        elif fmt == LogFormat.BLUE:
            self._active_color = "log_blue"
        elif fmt == LogFormat.CYAN:
            self._active_color = "log_cyan"
        elif fmt == LogFormat.GREEN:
            self._active_color = "log_green"
        elif fmt == LogFormat.DEFAULT:
            self._active_color = None

    def flush(self) -> None:
        if not self._segments:
            return

        if self.log_level in (LogLevel.WARN, LogLevel.ERROR, LogLevel.FATAL):
            console = self._problems_console
        else:
            console = self._output_console

        has_style = any(tags for _, tags in self._segments)
        if has_style:
            console.write_formatted(self._segments)
        else:
            text = "".join(seg_text for seg_text, _ in self._segments)
            console.write(text)
        self._segments.clear()


class Console(TextView):
    def __init__(self, master: tk.Widget, contents: Optional[str] = None, **kw):
        super().__init__(master, contents, **kw)
        # Set the text to read only
        self._text.configure(state=DISABLED)
        self._text.tag_configure("log_red", foreground="#cc0000")
        self._text.tag_configure("log_blue", foreground="#0000cc")
        self._text.tag_configure("log_cyan", foreground="#007080")
        self._text.tag_configure("log_green", foreground="#007000")
        base_font = tkfont.Font(font=self._text.cget("font"))
        self._text.tag_configure(
            "log_bold",
            font=tkfont.Font(
                family=base_font.actual("family"),
                size=base_font.actual("size"),
                weight="bold",
            ),
        )
        self._text.tag_configure("log_underline", underline=True)

    def write(self, contents: str) -> None:
        self._text.configure(state=NORMAL)
        self._text.insert(END, contents)
        self._text.see(END)
        self._text.configure(state=DISABLED)

    def write_formatted(self, segments: List[Tuple[str, FrozenSet[str]]]) -> None:
        self._text.configure(state=NORMAL)

        for seg_text, tags in segments:
            base = self._text.index("end-1c")
            self._text.insert(END, seg_text)
            end = self._text.index("end-1c")
            if tags:
                for tag in tags:
                    self._text.tag_add(tag, f"{base}", f"{end}")

        self._text.see("end")
        self._text.configure(state=DISABLED)


class ConsoleWithMessagesCounter(Console):
    def __init__(
        self,
        master: tk.Widget,
        contents: Optional[str],
        on_count_update: Callable[[int], None],
        **kw,
    ):
        super().__init__(master, contents, **kw)
        self._messages_count = 0
        self._on_count_update = on_count_update

    def _increment_messages_counter(self):
        if self._messages_count:
            super().write("\n")
        self._messages_count += 1
        self._on_count_update(self._messages_count)

    def write(self, contents: str) -> None:
        if contents:
            self._increment_messages_counter()
            super().write(contents)

    def write_formatted(self, segments: List[Tuple[str, FrozenSet[str]]]) -> None:
        if segments:
            self._increment_messages_counter()
            super().write_formatted(segments)


class ConsolesPanel(ttk.Notebook):
    def __init__(self, master: tk.Widget):
        super().__init__(master)
        self._output_console = Console(self, height=10)
        self._problems_console = ConsoleWithMessagesCounter(
            self, None, height=10, on_count_update=self._update_problems_tab_title
        )
        self.add(self._output_console, text="Output")
        self.add(self._problems_console, text="Problems")

    def _update_problems_tab_title(self, count: int) -> None:
        if count > 0:
            self.tab(self._problems_console, text=f"Problems ({count})")
            self.select(self._problems_console)

    def get_console_logger(
        self, get_relative_path: Callable[[str], str]
    ) -> ConsoleLogger:
        return ConsoleLogger(
            self._output_console, self._problems_console, get_relative_path
        )
