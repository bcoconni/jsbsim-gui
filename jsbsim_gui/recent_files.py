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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .options import Options, get_options

FILE_MANAGEMENT_KEY = "file_management"
RECENT_FILES_KEY = "recent_files"


@dataclass
class FileManagementOptions:
    num_recent_files: int = 5


class RecentFiles(Options):
    def __init__(self) -> None:
        options = get_options().get(FILE_MANAGEMENT_KEY)
        self._file_options = FileManagementOptions(**options)
        super().__init__("recent_files.json")

    def add_recent_file(self, file_path: Path, root_dir: Path):
        num_recent_files = self._file_options.num_recent_files
        new_entry = (file_path, root_dir)
        recent_files = self.get(RECENT_FILES_KEY)
        try:
            index = recent_files.index(new_entry)
            if index == 0:
                return

            if index + 1 == num_recent_files:
                recent_files = [new_entry] + recent_files[:-1]
            else:
                before = recent_files[:index]
                after = recent_files[index + 1 :]
                recent_files = [new_entry] + before + after
        except ValueError:
            if len(recent_files) >= num_recent_files:
                recent_files = [new_entry] + recent_files[:num_recent_files]
            else:
                recent_files = [new_entry] + recent_files

        self.set(RECENT_FILES_KEY, recent_files)
        self._save()

    def set(self, name: str, recent_files: list[tuple[Path, Path]]):
        super().set(name, [[str(entry[0]), str(entry[1])] for entry in recent_files])

    def get(self, name: str) -> list[tuple[Path, Path]]:
        return [
            (Path(entry[0]).resolve(), Path(entry[1]).resolve())
            for entry in self._options.get(name, [])
        ]

    def _load(self) -> None:
        super()._load()
        recent_files = self.get(RECENT_FILES_KEY)
        num_recent_files = self._file_options.num_recent_files

        if len(recent_files) > num_recent_files:
            self.set(RECENT_FILES_KEY, recent_files[:num_recent_files])

    def menu(
        self, master: tk.Widget, open_file: Callable[[Path, Path], None]
    ) -> tk.Menu:
        menu = tk.Menu(master, tearoff=False)

        def generate_add_menu_command(file: tuple[Path, Path]):
            # Capture the value of `file`
            def menu_command(
                menu: tk.Menu, file_name: Path, open_file: Callable[[Path, Path], None]
            ):
                menu.add_command(label=str(file_name), command=lambda: open_file(*file))

            return menu_command

        for file in self.get(RECENT_FILES_KEY):
            file_name = Path(file[0]).resolve()
            try:
                home = Path.home()
                if file_name.is_relative_to(home):
                    file_name = "~" / file_name.relative_to(home)
            except RuntimeError:
                pass

            menu_add_command = generate_add_menu_command(file)
            menu_add_command(menu, file_name, open_file)

        return menu

    def __getitem__(self, index: int) -> tuple[Path, Path]:
        recent_files = self.get(RECENT_FILES_KEY)
        return recent_files[index]

    def pretty_list(self) -> list[str]:
        recent_files = self.get(RECENT_FILES_KEY)
        try:
            home = Path.home()
            file_paths: list[Path] = []
            for file in recent_files:
                file_name = Path(file[0]).resolve()
                if file_name.is_relative_to(home):
                    file_paths.append("~" / file_name.relative_to(home))
        except RuntimeError:
            file_paths = [entry[0] for entry in recent_files]

        return [str(file_path) for file_path in file_paths]
