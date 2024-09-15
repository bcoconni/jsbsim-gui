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

from PySide6.QtCore import Qt, QFile
from PySide6.QtGui import QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QLabel,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from .controller import Controller
from .hierarchical_tree import HierarchicalTree, PropertyExplorer


class SourceEditor(QSplitter):
    def __init__(self, controller: Controller):
        super().__init__(Qt.Horizontal)

        # self.setMinimumSize(800, 600)
        left_column = QSplitter(Qt.Vertical)
        project_widget = QWidget()
        layout = QVBoxLayout(project_widget)
        layout.addWidget(QLabel("Project files"))
        project_files = HierarchicalTree(controller.get_input_files(), ["Files"], True)
        project_files.setHeaderHidden(True)
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

        text_editor = QTextEdit()
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font_metrics = QFontMetrics(font)
        text_size = font_metrics.size(0, ("X" * 80 + "\n") * 30)
        text_editor.setMinimumSize(text_size)
        text_editor.setFont(font)
        text_editor.setLineWrapMode(QTextEdit.NoWrap)
        self.addWidget(text_editor)

        in_file = QFile(controller.filename)
        if in_file.open(QFile.ReadOnly | QFile.Text):
            text_editor.setPlainText(in_file.readAll().data().decode())
        else:
            reason = in_file.errorString()
            QMessageBox.warning(
                self,
                "Script / aircraft file",
                f"Cannot read file {controller.filename}:\n{reason}.",
            )
            return
