# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2024 Bertrand Coconnier
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

from pathlib import Path
from tkinter.messagebox import showerror
from xml.parsers import expat

from .controller import Controller


class FileState:
    def __init__(self, filepath: Path, content: str):
        self.filepath = filepath
        self.content = content
        self.is_modified = False

    def write(self, root_dir: Path) -> bool:
        full_path = (root_dir / self.filepath).resolve()
        default_root = Controller.get_default_root_dir().resolve()
        try:
            if full_path.is_relative_to(default_root):
                showerror(
                    "Cannot Save File",
                    message=f'Cannot save "{self.filepath}": file is located in the JSBSim default root directory.',
                )
                return False
        except ValueError:
            pass

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(self.content)
            self.is_modified = False
            return True
        except IOError as e:
            showerror(
                "Save Error", message=f'Could not save "{self.filepath}":\n{str(e)}'
            )
            return False

    def validate_xml(self) -> tuple[int, int] | None:
        parser = expat.ParserCreate()
        try:
            parser.Parse(self.content, True)
            return None
        except expat.ExpatError as e:
            showerror(
                "XML Validation Error",
                message=f'XML error in "{self.filepath}" at line {e.lineno}, column {e.offset}:\n{str(e)}',
            )
            return e.offset, e.lineno
