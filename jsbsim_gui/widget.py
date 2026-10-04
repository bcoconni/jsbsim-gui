# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
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
from typing import Callable, Optional

from .edit_actions import EditAction, EditableFrame, SHORTCUT_MODIFIER


def widget_is_descendant(
    widget: Optional[tk.Misc], container: Optional[tk.Widget]
) -> bool:
    if not (widget and container):
        return False

    return str(widget).startswith(str(container))


class AutoClearLabel(ttk.Label):
    def __init__(self, master: tk.Tk, **kw):
        super().__init__(master, **kw)
        self._clear_timer_id: Optional[str] = None

    def set_text(self, message: str, duration_ms=2000) -> None:
        if self._clear_timer_id is not None:
            self.after_cancel(self._clear_timer_id)

        self.config(text=message)
        self._clear_timer_id = self.after(duration_ms, self._clear_text)

    def _clear_text(self):
        self.config(text="")
        self._clear_timer_id = None


class LabeledWidget(EditableFrame):
    def __init__(
        self,
        master: tk.Widget,
        label: str,
        collapsable: bool = False,
        on_toggle: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__(master)
        self.widget: Optional[EditableFrame] = None
        self._collapsed = False
        self._on_toggle = on_toggle
        if collapsable:
            self._label = ttk.Button(
                self, text=label, style="Flat.TButton", command=self._toggle_widget
            )
            self._label.grid(column=0, row=0, sticky="nsew")
        else:
            self._label = ttk.Label(self, text=label, anchor="center")
            self._label.grid(column=0, row=0, sticky="nsew", ipadx=5, ipady=5)
        self._label.columnconfigure(0, weight=1)

    def set_widget(self, widget: EditableFrame) -> None:
        self.widget = widget
        self.widget.grid(column=0, row=1, sticky=tk.NSEW)
        if self._collapsed:
            self.widget.grid_remove()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def set_label(self, label: str) -> None:
        self._label.config(text=label)

    def _toggle_widget(self) -> None:
        if self.widget is None:
            return

        if self._collapsed:
            self._label.config(style="Flat.TButton")
            self.widget.grid()
        else:
            self._label.config(style="TButton")
            self.widget.grid_remove()
        self._collapsed = not self._collapsed
        if self._on_toggle is not None:
            self._on_toggle(self._collapsed)

    def apply_edit_action(self, action: EditAction) -> None:
        if self.widget is not None:
            self.widget.apply_edit_action(action)


class TextBox(ttk.Entry):
    def __init__(self, master: tk.Widget, hint_message: str = "", **kw):
        if hint_message and "textvariable" not in kw:
            kw["textvariable"] = tk.StringVar(master)
        super().__init__(master, **kw)
        self.bind(f"<{SHORTCUT_MODIFIER}-a>", self._select_all)
        if hint_message:
            # The hint is a label laid over the entry so that the entry content
            # (and its textvariable) never contains the default text.
            field_background = ttk.Style(master).lookup("TEntry", "fieldbackground")
            self._hint = tk.Label(
                self,
                text=hint_message,
                foreground="gray75",
                background=field_background or "white",
                anchor=tk.W,
                cursor="xterm",
            )
            self._hint.bind("<Button-1>", lambda _: self.focus_set())
            self._textvariable = kw["textvariable"]
            self._trace_id = self._textvariable.trace_add("write", self._update_hint)
            self._has_focus = False
            self.bind("<FocusIn>", self._on_focus_in, add="+")
            self.bind("<FocusOut>", self._on_focus_out, add="+")
            self.bind("<Destroy>", self._on_destroy, add="+")
            self._update_hint()

    def _update_hint(self, *_) -> None:
        if self.get() or self._has_focus:
            self._hint.place_forget()
        else:
            self._hint.place(x=2, y=2, relwidth=1.0, width=-4, relheight=1.0, height=-4)

    def _on_focus_in(self, *_) -> None:
        self._has_focus = True
        self._hint.place_forget()

    def _on_focus_out(self, *_) -> None:
        self._has_focus = False
        self._update_hint()

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self._textvariable.trace_remove("write", self._trace_id)

    def _select_all(self, *_) -> str:
        self.selection_range(0, tk.END)
        # Return break to interrupt the default key binding.
        return "break"
