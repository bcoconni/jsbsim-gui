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

import csv
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import ttkbootstrap as ttk

from .hierarchical_tree import HierarchicalTree, SearchableTree


@dataclass
class CsvData:
    path: Path
    name: str
    time: np.ndarray
    data: np.ndarray


class CsvTree(SearchableTree):
    def __init__(self, master: tk.Widget):
        super().__init__(
            master,
            lambda parent: HierarchicalTree(parent, [], [], is_open=True),
        )
        self.tree.configure_tree(show="tree", selectmode="extended")
        self._item_id_to_column: dict[str, CsvData] = {}
        self._loaded_files: list[Path] = []

    def has_loaded_files(self) -> bool:
        return bool(self._loaded_files)

    def load_csv(self, csv_path: Path) -> None:
        if csv_path in self._loaded_files:
            return

        try:
            with open(csv_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)
        except (OSError, csv.Error) as exc:
            ttk.Messagebox.show_error(str(exc), "Error loading CSV")
            return

        if len(headers) < 2 or not rows:
            ttk.Messagebox.show_error(
                f"No data columns found in {csv_path.name}.", "Error loading CSV"
            )
            return

        try:
            data = np.array([[float(v) for v in row] for row in rows])
        except ValueError as exc:
            ttk.Messagebox.show_error(
                f"Non-numeric value in {csv_path.name}: {exc}", "Error loading CSV"
            )
            return

        time_array = data[:, 0]
        file_node_id = self.tree.insert("", tk.END, text=csv_path.name, open=True)
        self._loaded_files.append(csv_path)

        for col_idx, col_name in enumerate(headers[1:], start=1):
            col_id = self.tree.insert(file_node_id, tk.END, text=col_name)
            self._item_id_to_column[col_id] = CsvData(
                csv_path, col_name, time_array, data[:, col_idx]
            )

    def get_selected_csv_columns(self) -> list[CsvData]:
        result: list[CsvData] = []
        for item_id in self.tree.selection():
            children = self.tree.get_children(item_id)
            if children:
                for col_id in children:
                    result.append(self._item_id_to_column[col_id])
            else:
                result.append(self._item_id_to_column[item_id])
        return result
