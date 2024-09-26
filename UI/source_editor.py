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

import os

from PySide6.QtCore import Qt, QFile, Slot
from PySide6.QtGui import QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QLabel,
    QSplitter,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from .controller import Controller
from .hierarchical_tree import FileTree, PropertyExplorer
from .code_editor import QCodeEditor, XMLHighlighter


class SourceEditor(QSplitter):
    def __init__(self, controller: Controller):
        super().__init__(Qt.Horizontal)
        self.controller = controller

        # self.setMinimumSize(800, 600)
        left_column = QSplitter(Qt.Vertical)
        project_widget = QWidget()
        layout = QVBoxLayout(project_widget)
        layout.addWidget(QLabel("Project files"))
        project_files = FileTree(controller.get_input_files())
        project_files.file_selected.connect(self.open_file)
        project_files.setMinimumWidth(250)
        layout.addWidget(project_files)
        left_column.addWidget(layout.parentWidget())
        property_widget = QWidget()
        property_explorer = PropertyExplorer(
            property_widget,
            controller.get_property_list(),
            controller.get_property_root().get_fully_qualified_name(),
        )
        left_column.addWidget(property_explorer.parentWidget())
        self.addWidget(left_column)

        self.text_editor = QCodeEditor(True, True, XMLHighlighter)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font_metrics = QFontMetrics(font)
        text_size = font_metrics.size(0, ("X" * 80 + "\n") * 30)
        self.text_editor.setMinimumSize(text_size)
        self.text_editor.setFont(font)
        self.text_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.addWidget(self.text_editor)
        self.load_file(controller.filename)

    @Slot(str)
    def open_file(self, filename: str) -> None:
        self.load_file(os.path.join(self.controller.get_root_dir(), filename))

    def load_file(self, filename: str) -> None:
        in_file = QFile(filename)
        if in_file.open(QFile.ReadOnly | QFile.Text):
            self.text_editor.clear()
            self.text_editor.setPlainText(in_file.readAll().data().decode())
        else:
            reason = in_file.errorString()
            QMessageBox.warning(
                self,
                "Script / aircraft file",
                f"Cannot read file {filename}:\n{reason}.",
            )
