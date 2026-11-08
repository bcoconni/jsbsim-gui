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

from dataclasses import asdict, dataclass
import re
import sys
import tkinter as tk
from tkinter import colorchooser, font as tkfont, ttk, TclError
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
from typing import Callable, Literal

from pygments import lex
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Name, String, Text, _TokenType

from .edit_actions import REDO_SHORTCUT, SHORTCUT_MODIFIER, EditAction, EditableFrame
from .options import get_options, OptionsTab


class TextView(EditableFrame):
    """Display text with scrollbar(s)"""

    def __init__(
        self,
        master: tk.Widget,
        contents: str | None = None,
        frame_column: int = 0,
        **kw,
    ):
        super().__init__(master)
        self._text = tk.Text(self, **kw)
        self._focus_timer: str | None = None
        self._text.bind("<Destroy>", self._cancel_pending_focus, add="+")
        self._text.grid(column=frame_column, row=0, sticky=NSEW)

        # Vertical scrollbar
        self._yscrollbar = ttk.Scrollbar(
            self, orient=VERTICAL, command=self._text.yview
        )
        self._yscrollbar.grid(column=frame_column + 1, row=0, sticky=NS)
        self._text["yscrollcommand"] = self._yscrollbar.set

        # Horizontal scrollbar if the text is not wrapped
        if "wrap" in kw and kw["wrap"] == NONE:
            self.xscrollbar: ttk.Scrollbar | None = ttk.Scrollbar(
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
        self._text.bind("<Return>", self._auto_indent)
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

    def _auto_indent(self, _event: tk.Event) -> str:
        line_head = self._text.get("insert linestart", tk.INSERT)
        match = re.match(r"^([ \t]*)", line_head)
        whitespaces = match.group(1) if match else ""
        self._text.config(autoseparators=False)
        self._text.edit_separator()
        self._text.insert(tk.INSERT, "\n" + whitespaces)
        self._text.edit_separator()
        self._text.config(autoseparators=True)
        return "break"

    def new_content(self, contents: str) -> None:
        self._text.delete("1.0", END)
        self._text.insert("1.0", contents)
        self.move_cursor("1.0")
        self._text.edit_modified(False)
        self._text.edit_reset()

    def get_content(self) -> str:
        return self._text.get("1.0", "end-1c")

    def focus_text(self) -> None:
        self._text.focus_set()

    def _cancel_pending_focus(self, event: tk.Event) -> None:
        if event.widget is self._text and self._focus_timer is not None:
            self.after_cancel(self._focus_timer)
            self._focus_timer = None

    def _focus_after_idle(self) -> None:
        self._focus_timer = None
        self._text.focus_set()

    def move_cursor(self, position: str, focus: bool = True) -> None:
        self._text.mark_set(tk.INSERT, f"{position}")
        self._text.see(tk.INSERT)
        if focus:
            if self._focus_timer is not None:
                self.after_cancel(self._focus_timer)
            self._focus_timer = self.after_idle(self._focus_after_idle)

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
        func: Callable[[tk.Event], object],
        add: bool | Literal["", "+"] | None = None,
    ) -> str:
        return self._text.bind(sequence, func, add)


@dataclass
class SourceCodeViewOptions:
    active_line_color: str = "#fff2cc"
    selection_color: str = "#c3d9ff"
    highlight_active_line: bool = True
    bold_line_number: bool = True


SOURCE_CODE_VIEW_OPTIONS_KEY = "source_code_view"


class SourceCodeView(TextView):
    """Display text with line numbers"""

    HIGHLIGHT_DELAY_MS = 300
    ACTIVE_LINE_TAG = "active_line"

    def __init__(self, master: tk.Widget, contents: str | None = None, **kw):
        # Override parameters defined upstream
        kw["borderwidth"] = 0
        kw["relief"] = FLAT
        super().__init__(master, frame_column=1, undo=True, **kw)
        self._modified_text_callbacks: list[Callable[[bool], None]] = []
        self._highlight_timer: str | None = None
        self._lexer: Lexer | None = None

        self._line_numbers = tk.Text(
            self,
            width=1,
            height=int(self._text.cget("height")),
            bg="#eeeeee",
            borderwidth=0,
            relief=FLAT,
            wrap=NONE,
        )
        # Even when empty, the first line is where the cursor is so we need a number
        self._line_numbers.insert("1.0", "1")
        self._line_numbers.grid(column=0, row=0, sticky=NS)
        self._active_line_number_font = tkfont.nametofont(
            self._line_numbers.cget("font")
        ).copy()
        self._line_numbers.tag_configure(
            self.ACTIVE_LINE_TAG, font=self._active_line_number_font
        )

        self._load_display_options()
        self._text.tag_lower(self.ACTIVE_LINE_TAG, tk.SEL)
        get_options().subscribe(
            SOURCE_CODE_VIEW_OPTIONS_KEY, self._load_display_options
        )
        # Explicitly calls `SourceCodeView._on_destroy`, because `self._on_destroy`
        # could call the method `_on_destroy` from an inherited instance.
        self.bind("<Destroy>", lambda e: SourceCodeView._on_destroy(self, e), add="+")

        self._line_numbers.bind("<Button-1>", self._goto_line)
        self._line_numbers.bind("<MouseWheel>", self._on_line_numbers_scroll)
        self._line_numbers.bind("<Button-4>", self._on_line_numbers_scroll)
        self._line_numbers.bind("<Button-5>", self._on_line_numbers_scroll)
        self._line_numbers.configure(state=DISABLED)

        self._text.bind("<KeyRelease>", self._update_active_line, add="+")
        self._text.bind("<ButtonRelease-1>", self._update_active_line, add="+")
        self._text["yscrollcommand"] = self._move_line_numbers
        self._yscrollbar.configure(command=self._yview)
        self._modified_event_id = self._text.bind(
            "<<Modified>>", self._on_text_modified
        )
        self._text.bind("<Destroy>", self._cancel_highlighting, add="+")

        if contents:
            self.new_content(contents)
        self._update_active_line()

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget == self._text:
            get_options().unsubscribe(
                SOURCE_CODE_VIEW_OPTIONS_KEY, self._load_display_options
            )

    def _cancel_highlighting(self, event: tk.Event) -> None:
        if event.widget is self._text and self._highlight_timer:
            self.after_cancel(self._highlight_timer)
            self._highlight_timer = None

    def _load_display_options(self) -> None:
        options = get_options().get(SOURCE_CODE_VIEW_OPTIONS_KEY)
        display_options = SourceCodeViewOptions(**options)
        self.set_display_options(display_options)

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
        self._update_active_line()

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

    def _get_highlight_tags(self) -> list[str]:
        return []

    def _get_tag_name(self, _token: _TokenType) -> str | None:
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
        self._update_active_line()
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

    def _update_active_line(self, _event: tk.Event | None = None) -> None:
        line = self._text.index(f"{tk.INSERT} linestart").split(".", maxsplit=1)[0]
        for widget in (self._text, self._line_numbers):
            widget.tag_remove(self.ACTIVE_LINE_TAG, "1.0", END)
            if not self._text.tag_ranges(tk.SEL):
                widget.tag_add(
                    self.ACTIVE_LINE_TAG,
                    f"{line}.0",
                    f"{line}.end + 1 chars",
                )

    def set_display_options(self, options: SourceCodeViewOptions) -> None:
        self._text.configure(
            selectbackground=options.selection_color,
            inactiveselectbackground=options.selection_color,
        )
        self._active_line_number_font.configure(
            weight="bold" if options.bold_line_number else "normal"
        )
        background = options.active_line_color if options.highlight_active_line else ""
        self._text.tag_configure(self.ACTIVE_LINE_TAG, background=background)
        self._line_numbers.tag_configure(self.ACTIVE_LINE_TAG, background=background)

    def move_cursor(self, position: str, focus: bool = True) -> None:
        super().move_cursor(position, focus)
        self._update_active_line()

    def select_text(self, text: str, position: str) -> None:
        super().select_text(text, position)
        self._update_active_line()

    def apply_edit_action(self, action: EditAction) -> None:
        super().apply_edit_action(action)
        self._update_active_line()


@dataclass
class XMLSyntaxColors:
    tag: str = "#ff00ff"
    comment: str = "#00aaaa"
    attribute_name: str = "#00aa00"
    attribute_value: str = "#aaaa00"
    data: str = "#000000"


XML_SYNTAX_COLORS_KEY = "xml_syntax_colors"


class XMLSourceCodeView(SourceCodeView):
    def __init__(self, master: tk.Widget, contents: str | None = None, **kw):
        super().__init__(master, contents, **kw)

        self._load_syntax_colors()
        get_options().subscribe(XML_SYNTAX_COLORS_KEY, self._load_syntax_colors)

        # Explicitly calls `XMLSourceCodeView._on_destroy`, because `self._on_destroy`
        # could call the method `_on_destroy` from an inherited instance.
        self.bind(
            "<Destroy>", lambda e: XMLSourceCodeView._on_destroy(self, e), add="+"
        )

        self._lexer = get_lexer_by_name("xml")
        if contents:
            self.highlight_text()

    def _load_syntax_colors(self):
        options_colors = get_options().get(XML_SYNTAX_COLORS_KEY)
        colors = XMLSyntaxColors(**options_colors)
        self.set_syntax_colors(colors)

    def set_syntax_colors(self, colors: XMLSyntaxColors) -> None:
        for tag, color in asdict(colors).items():
            self._text.tag_configure("XML_" + tag, foreground=color)

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget == self._text:
            get_options().unsubscribe(XML_SYNTAX_COLORS_KEY, self._load_syntax_colors)

    def _get_highlight_tags(self) -> list[str]:
        return ["XML_" + tag for tag in asdict(XMLSyntaxColors()).keys()]

    def _get_tag_name(self, token: _TokenType) -> str | None:
        if token in Name.Tag:
            return "XML_tag"
        if token in Comment:
            return "XML_comment"
        if token in Name.Attribute:
            return "XML_attribute_name"
        if token in String:
            return "XML_attribute_value"
        if token in Text:
            return "XML_data"
        return None

    def new_content(self, contents: str) -> None:
        super().new_content(contents)
        self.highlight_text()

    def extract_tagged_regions(self, tag_name: str) -> list[tuple[int, int, str]]:
        tagged_regions = []
        ranges = self._text.tag_ranges(tag_name)
        for i in range(0, len(ranges), 2):
            start_index = str(ranges[i])
            end_index = str(ranges[i + 1])

            line, column = map(int, start_index.split("."))
            text = self._text.get(start_index, end_index)
            tagged_regions.append((line, column, text))

        return tagged_regions


SAMPLE_XML = """<!-- Example XML script -->
<channel name="Pitch">
    <summer name="Pitch Trim">
        <input>fcs/elevator-cmd-norm</input>
    </summer>
</channel>"""


class ColorChooser(ttk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        label: str,
        color: str,
        on_color_changed: Callable[[str], None],
        **kw,
    ):
        super().__init__(master, **kw)
        self._label = label
        self._color = color
        self._on_color_changed = on_color_changed

        cursor_name = "pointinghand" if sys.platform == "darwin" else "hand2"
        ttk.Label(self, text=label).grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.swatch = tk.Canvas(
            self,
            width=36,
            height=18,
            background=color,
            relief="solid",
            highlightthickness=1,
            cursor=cursor_name,
        )
        self.swatch.grid(row=0, column=1, padx=8, pady=4)
        self.swatch.bind("<Button-1>", lambda _event: self.choose_color())

        self.hex_label = ttk.Label(self, text=color, width=9)
        self.hex_label.grid(row=0, column=2, padx=5, pady=4)

        ttk.Button(self, text="Choose...", command=self.choose_color).grid(
            row=0, column=3, padx=5, pady=4
        )
        self.grid_columnconfigure(0, weight=1)

    def set_color(self, color: str) -> None:
        self._color = color
        self.swatch.configure(background=color)
        self.hex_label.configure(text=color)

    def choose_color(self) -> None:
        label = self._label[0].upper() + self._label[1:]
        chosen = colorchooser.askcolor(
            color=self._color,
            parent=self,
            title=f"Choose {label} Color",
        )
        if chosen and chosen[1]:
            color = chosen[1]
            self.set_color(color)
            self._on_color_changed(color)


class TextViewOptionsTab(OptionsTab):
    def __init__(self, master: tk.Tk | tk.Toplevel, **kw):
        super().__init__(master, padding=10, **kw)
        options = get_options()
        options_colors = options.get(XML_SYNTAX_COLORS_KEY)
        options_display = options.get(SOURCE_CODE_VIEW_OPTIONS_KEY)
        self._initial_colors = XMLSyntaxColors(**options_colors)
        self._current_colors = XMLSyntaxColors(**options_colors)
        self._initial_display_options = SourceCodeViewOptions(**options_display)
        self._current_display_options = SourceCodeViewOptions(**options_display)

        settings_frame = ttk.Frame(self)
        settings_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        display_frame = ttk.LabelFrame(settings_frame, text="Editor", padding=10)
        display_frame.pack(fill=tk.X)

        colors_frame = ttk.LabelFrame(settings_frame, text="XML Colors", padding=10)
        colors_frame.pack(fill=tk.X, pady=(0, 5))

        self._color_choosers: dict[str, ColorChooser] = {}
        self._swatches: dict[str, tk.Canvas] = {}
        self._hex_labels: dict[str, ttk.Label] = {}

        tags = asdict(self._current_colors).keys()
        for row_idx, tag in enumerate(tags):
            color = getattr(self._current_colors, tag)
            label_text = tag[0].upper() + tag[1:].replace("_", " ")
            self._add_color_chooser(
                colors_frame,
                row_idx,
                tag,
                label_text,
                color,
                lambda new_color, name=tag: self._set_syntax_color(name, new_color),
            )
        colors_frame.grid_columnconfigure(0, weight=1)

        self._highlight_active_line_var = tk.BooleanVar(
            self, value=self._current_display_options.highlight_active_line
        )
        ttk.Checkbutton(
            display_frame,
            text="Highlight active line",
            variable=self._highlight_active_line_var,
            command=self._update_display_options,
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=4)

        self._bold_line_number_var = tk.BooleanVar(
            self, value=self._current_display_options.bold_line_number
        )
        ttk.Checkbutton(
            display_frame,
            text="Bold line number",
            variable=self._bold_line_number_var,
            command=self._update_display_options,
        ).grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=5, pady=4)
        display_frame.grid_columnconfigure(0, weight=1)

        self._add_color_chooser(
            display_frame,
            2,
            "active_line_color",
            "Active line",
            self._current_display_options.active_line_color,
            lambda color: self._set_display_color("active_line_color", color),
        )
        self._add_color_chooser(
            display_frame,
            3,
            "selection_color",
            "Selection",
            self._current_display_options.selection_color,
            lambda color: self._set_display_color("selection_color", color),
        )

        # Preview section
        preview_frame = ttk.LabelFrame(self, text="Preview", padding=5)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._preview = XMLSourceCodeView(preview_frame, SAMPLE_XML, width=45, height=6)
        self._preview._text.configure(state=tk.DISABLED)
        self._preview.pack(fill=tk.BOTH, expand=True)

    def _add_color_chooser(
        self,
        frame: ttk.LabelFrame,
        row: int,
        name: str,
        label: str,
        color: str,
        on_color_changed: Callable[[str], None],
    ) -> None:
        chooser = ColorChooser(frame, label, color, on_color_changed)
        chooser.grid(row=row, column=0, sticky=tk.EW)
        self._color_choosers[name] = chooser
        self._swatches[name] = chooser.swatch
        self._hex_labels[name] = chooser.hex_label

    def _choose_color(self, tag: str) -> None:
        self._color_choosers[tag].choose_color()

    def _set_syntax_color(self, tag: str, color: str) -> None:
        setattr(self._current_colors, tag, color)
        self._preview.set_syntax_colors(self._current_colors)

    def _set_display_color(self, name: str, color: str) -> None:
        setattr(self._current_display_options, name, color)
        self._preview.set_display_options(self._current_display_options)

    def _update_display_options(self) -> None:
        self._current_display_options.highlight_active_line = (
            self._highlight_active_line_var.get()
        )
        self._current_display_options.bold_line_number = (
            self._bold_line_number_var.get()
        )
        self._preview.set_display_options(self._current_display_options)

    def restore_defaults(self) -> None:
        self._current_colors = XMLSyntaxColors()
        for tag, color in asdict(self._current_colors).items():
            self._color_choosers[tag].set_color(color)
        self._preview.set_syntax_colors(self._current_colors)

        self._current_display_options = SourceCodeViewOptions()
        for name in ("active_line_color", "selection_color"):
            color = getattr(self._current_display_options, name)
            self._color_choosers[name].set_color(color)
        self._highlight_active_line_var.set(
            self._current_display_options.highlight_active_line
        )
        self._bold_line_number_var.set(self._current_display_options.bold_line_number)
        self._preview.set_display_options(self._current_display_options)

    def apply(self) -> None:
        self._update_display_options()
        get_options().set(XML_SYNTAX_COLORS_KEY, asdict(self._current_colors))
        get_options().set(
            SOURCE_CODE_VIEW_OPTIONS_KEY, asdict(self._current_display_options)
        )

    def cancel(self) -> None:
        get_options().set(XML_SYNTAX_COLORS_KEY, asdict(self._initial_colors))
        get_options().set(
            SOURCE_CODE_VIEW_OPTIONS_KEY, asdict(self._initial_display_options)
        )
