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

import json
import tkinter as tk

from abc import ABC, abstractmethod
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable, List, Optional, Union

import platformdirs


def get_options_file_path(app_name: str = "jsbsim-gui") -> Path:
    return Path(platformdirs.user_config_dir(app_name)) / "options.json"


class Options:
    def __init__(self):
        self._file_path = get_options_file_path()
        self._options: dict[str, Any] = {"version": "0.1"}
        self._subscribers: dict[str, List[Callable[[], None]]] = {}
        self.load()

    def get(self, name: str) -> Any:
        return self._options.get(name, {})

    def set(self, name: str, value: dict[str, Any]) -> None:
        self._options[name] = value

        if name in self._subscribers:
            for callback in self._subscribers[name]:
                callback()

    def subscribe(self, name: str, callback: Callable[[], None]) -> None:
        if name not in self._subscribers:
            self._subscribers[name] = [callback]
            return

        if callback not in self._subscribers[name]:
            self._subscribers[name].append(callback)

    def unsubscribe(self, name: str, callback: Callable[[], None]) -> None:
        assert name in self._subscribers and callback in self._subscribers[name]
        self._subscribers[name].remove(callback)

    def load(self) -> None:
        if not self._file_path.is_file():
            return

        with open(self._file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                self._options = data

    def save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._options, f, indent=4)


class OptionsTab(ttk.Frame, ABC):
    def __init__(self, master: Union[tk.Tk, tk.Toplevel], **kw):
        super().__init__(master, **kw)

    @abstractmethod
    def apply(self) -> None: ...

    @abstractmethod
    def cancel(self) -> None: ...

    @abstractmethod
    def restore_defaults(self) -> None: ...


class OptionsWindow(tk.Toplevel):
    def __init__(self, master: Union[tk.Tk, tk.Toplevel], **kw):
        super().__init__(master, **kw)
        self.title("Options")
        self.resizable(False, False)

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # Buttons frame
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(
            button_frame, text="Restore Defaults", command=self._restore_defaults
        ).pack(side=tk.LEFT)

        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(button_frame, text="Apply", command=self._apply).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(button_frame, text="OK", command=self._ok).pack(
            side=tk.RIGHT, padx=5
        )

    def _ok(self) -> None:
        active_tab = self._notebook.nametowidget(self._notebook.select())
        assert isinstance(active_tab, OptionsTab)
        active_tab.apply()
        get_options().save()
        self.destroy()

    def _apply(self) -> None:
        active_tab = self._notebook.nametowidget(self._notebook.select())
        assert isinstance(active_tab, OptionsTab)
        active_tab.apply()

    def _cancel(self) -> None:
        active_tab = self._notebook.nametowidget(self._notebook.select())
        assert isinstance(active_tab, OptionsTab)
        active_tab.cancel()
        self.destroy()

    def _restore_defaults(self) -> None:
        active_tab = self._notebook.nametowidget(self._notebook.select())
        assert isinstance(active_tab, OptionsTab)
        active_tab.restore_defaults()

    def add_option_tab(self, option_tab: tk.Widget, title: str) -> None:
        self._notebook.add(option_tab, text=title)


_global_options: Optional[Options] = None


def get_options() -> Options:
    global _global_options
    if _global_options is None:
        _global_options = Options()
    return _global_options


def set_options(options: Optional[Options]) -> None:
    global _global_options
    _global_options = options
