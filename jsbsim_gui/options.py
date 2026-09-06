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
from pathlib import Path
from typing import Any, Callable, List, Optional
import platformdirs


def get_options_file_path(app_name: str = "jsbsim-gui") -> Path:
    return Path(platformdirs.user_config_dir(app_name)) / "options.json"


class Options:
    def __init__(self):
        self._file_path = get_options_file_path()
        self._options: dict[str, Any] = {"version": "0.1"}
        self._subscribers: List[Callable[[], None]] = []
        self.load()

    def get(self, name: str) -> Any:
        return self._options.get(name, {})

    def set(self, name: str, value: dict[str, Any]) -> None:
        self._options[name] = value

    def subscribe(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        assert callback in self._subscribers
        self._subscribers.remove(callback)

    def notify(self) -> None:
        for callback in list(self._subscribers):
            callback()

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


_global_options: Optional[Options] = None


def get_options() -> Options:
    global _global_options
    if _global_options is None:
        _global_options = Options()
    return _global_options


def set_options(options: Optional[Options]) -> None:
    global _global_options
    _global_options = options
