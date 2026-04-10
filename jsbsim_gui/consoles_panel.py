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

import copy
import enum
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import ttk
from tkinter.constants import DISABLED, END, NORMAL
from typing import Callable, ClassVar, List, Optional, Tuple

from jsbsim import FGLogger, LogFormat, LogLevel

from .textview import TextView


class LogColor(str, enum.Enum):
    RED = "log_red"
    BLUE = "log_blue"
    CYAN = "log_cyan"
    GREEN = "log_green"


@dataclass
class LogTags:
    color: Optional[LogColor] = None
    underline: bool = False
    bold: bool = False
    BOLD: ClassVar[str] = "log_bold"  # pylint: disable=invalid-name
    UNDERLINE: ClassVar[str] = "log_underline"  # pylint: disable=invalid-name

    def __iter__(self):
        if self.color is not None:
            yield self.color
        if self.underline:
            yield self.UNDERLINE
        if self.bold:
            yield self.BOLD


@dataclass
class LogSegment:
    text: str
    tags: LogTags
    file_link: Optional[Tuple[str, int]] = None


class Console(TextView):
    def __init__(
        self,
        master: tk.Widget,
        contents: Optional[str] = None,
        *,
        on_file_link_click: Callable[[str, int], None],
        **kw,
    ):
        super().__init__(master, contents, **kw)
        self._on_file_link_click = on_file_link_click
        self._file_link_counter: int = 0
        # Set the text to read only
        self._text.configure(state=DISABLED)
        self._text.tag_configure(LogColor.RED, foreground="#cc0000")
        self._text.tag_configure(LogColor.BLUE, foreground="#0000cc")
        self._text.tag_configure(LogColor.CYAN, foreground="#007080")
        self._text.tag_configure(LogColor.GREEN, foreground="#007000")
        base_font = tkfont.Font(font=self._text.cget("font"))
        bold_font = tkfont.Font(
            family=base_font.actual("family"),
            size=base_font.actual("size"),
            weight="bold",
        )
        self._text.tag_configure(LogTags.BOLD, font=bold_font)
        self._text.tag_configure(LogTags.UNDERLINE, underline=True)

    def write(self, contents: str) -> None:
        self._text.configure(state=NORMAL)
        self._text.insert(END, contents)
        self._text.see(END)
        self._text.configure(state=DISABLED)

    def write_formatted(self, segments: List[LogSegment]) -> None:
        self._text.configure(state=NORMAL)

        for segment in segments:
            base = self._text.index("end-1c")
            self._text.insert(END, segment.text)
            end = self._text.index("end-1c")
            for tag in segment.tags:
                self._text.tag_add(tag, base, end)
            if segment.file_link is not None:
                fl_tag = f"_fl_{self._file_link_counter}"
                self._file_link_counter += 1
                self._text.tag_add(fl_tag, base, end)
                self._text.tag_bind(
                    fl_tag,
                    "<Button-1>",
                    lambda _, fl=segment.file_link: self._on_file_link_click(*fl),
                )

        self._text.see(END)
        self._text.configure(state=DISABLED)


class ConsoleWithMessagesCounter(Console):
    def __init__(
        self,
        master: tk.Widget,
        contents: Optional[str],
        on_count_update: Callable[[int], None],
        on_file_link_click: Callable[[str, int], None],
        **kw,
    ):
        super().__init__(master, contents, on_file_link_click=on_file_link_click, **kw)
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

    def write_formatted(self, segments: List[LogSegment]) -> None:
        if segments:
            self._increment_messages_counter()
            super().write_formatted(segments)


class ConsoleLogger(FGLogger):
    def __init__(
        self,
        output_console: Console,
        problems_console: Console,
        get_file_relative_path: Callable[[str], str],
    ):
        super().__init__()
        self._output_console = output_console
        self._problems_console = problems_console
        self._get_file_relative_path = get_file_relative_path
        self._segments: List[LogSegment] = []
        self._tags = LogTags()

    def set_level(self, level: LogLevel) -> None:
        super().set_level(level)
        self._segments.clear()
        if level in (LogLevel.WARN, LogLevel.ERROR, LogLevel.FATAL):
            self._tags = LogTags(LogColor.RED, bold=True, underline=False)
            if level == LogLevel.WARN:
                self._tags.color = LogColor.CYAN
                self.message("WARNING: ")
            elif level == LogLevel.ERROR:
                self.message("ERROR: ")
            else:
                self.message("FATAL: ")
        self._tags = LogTags()

    def file_location(self, filename: str, line: int) -> None:
        rel_path = self._get_file_relative_path(filename)
        text = f"In {rel_path}: line {line}\n"
        tags = LogTags(self._tags.color, bold=self._tags.bold, underline=True)
        self._segments.append(LogSegment(text, tags, (rel_path, line)))

    def message(self, text: str) -> None:
        if self._segments:
            prev = self._segments[-1]
            if prev.file_link is None and self._tags == prev.tags:
                prev.text += text
                return

        self._segments.append(LogSegment(text, copy.copy(self._tags)))

    def format(self, fmt: LogFormat) -> None:
        if fmt == LogFormat.RESET:
            self._tags = LogTags()
        elif fmt == LogFormat.BOLD:
            self._tags.bold = True
        elif fmt == LogFormat.NORMAL:
            self._tags.bold = False
            self._tags.underline = False
        elif fmt == LogFormat.UNDERLINE_ON:
            self._tags.underline = True
        elif fmt == LogFormat.UNDERLINE_OFF:
            self._tags.underline = False
        elif fmt == LogFormat.RED:
            self._tags.color = LogColor.RED
        elif fmt == LogFormat.BLUE:
            self._tags.color = LogColor.BLUE
        elif fmt == LogFormat.CYAN:
            self._tags.color = LogColor.CYAN
        elif fmt == LogFormat.GREEN:
            self._tags.color = LogColor.GREEN
        elif fmt == LogFormat.DEFAULT:
            self._tags.color = None

    def flush(self) -> None:
        if not self._segments:
            return

        if self.log_level in (LogLevel.WARN, LogLevel.ERROR, LogLevel.FATAL):
            console = self._problems_console
        else:
            console = self._output_console

        has_format = any(any(s.tags) or s.file_link is not None for s in self._segments)
        if has_format:
            console.write_formatted(self._segments)
        else:
            console.write("".join(segment.text for segment in self._segments))
        self._segments.clear()


class ConsolesPanel(ttk.Notebook):
    def __init__(
        self, master: tk.Widget, on_file_link_click: Callable[[str, int], None], **kw
    ):
        super().__init__(master)
        self._output_console = Console(
            self, on_file_link_click=on_file_link_click, **kw
        )
        self._problems_console = ConsoleWithMessagesCounter(
            self,
            None,
            on_count_update=self._update_problems_tab_title,
            on_file_link_click=on_file_link_click,
            **kw,
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
