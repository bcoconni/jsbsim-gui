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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout, QLabel

from .controller import Controller
from .hierarchical_tree import HierarchicalTree, PropertyExplorer


class SourceEditor(QSplitter):
    def __init__(self, controller: Controller):
        super().__init__(Qt.Vertical)

        project_widget = QWidget()
        layout = QVBoxLayout(project_widget)
        layout.addWidget(QLabel("Project files"))
        project_files = HierarchicalTree(controller.get_input_files(), ["Files"], True)
        project_files.setHeaderHidden(True)
        layout.addWidget(project_files)
        self.addWidget(layout.parentWidget())
        property_widget = QWidget()
        property_explorer = PropertyExplorer(
            property_widget,
            controller.get_property_list(),
            controller.get_property_root().get_fully_qualified_name(),
        )
        self.addWidget(property_explorer.parentWidget())
