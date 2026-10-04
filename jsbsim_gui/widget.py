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
    def __init__(self, master: tk.Widget, **kw):
        super().__init__(master, **kw)
        self.bind(f"<{SHORTCUT_MODIFIER}-a>", self._select_all)

    def _select_all(self, *_) -> str:
        self.selection_range(0, tk.END)
        # Return break to interrupt the default key binding.
        return "break"
