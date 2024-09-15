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

from typing import List, Optional

from jsbsim import FGPropertyNode
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class HierarchicalTree(QTreeWidget):
    def __init__(
        self, items: List[str], headers_labels: List[str], expand: bool = False
    ):
        super().__init__()

        self.setHeaderLabels(headers_labels)

        folder_icon = QIcon()
        folder_icon.addPixmap(
            self.style().standardPixmap(QStyle.SP_DirClosedIcon),
            QIcon.Normal,
            QIcon.Off,
        )
        folder_icon.addPixmap(
            self.style().standardPixmap(QStyle.SP_DirOpenIcon), QIcon.Normal, QIcon.On
        )
        file_icon = QIcon()
        file_icon.addPixmap(self.style().standardPixmap(QStyle.SP_FileIcon))

        for elm in sorted(items):
            hierarchy = elm.split("/")
            name = hierarchy[0]
            nfolders = len(hierarchy) - 1
            for child_id in range(self.topLevelItemCount()):
                child = self.topLevelItem(child_id)
                if child.text(0) == name:
                    parent = child
                    break
            else:
                item = QTreeWidgetItem(self)
                item.setText(0, name)
                item.setExpanded(expand)
                if nfolders == 0:
                    item.setIcon(0, file_icon)
                    continue

                item.setIcon(0, folder_icon)
                parent = item

            for idx, name in enumerate(hierarchy[1:]):
                nchild = parent.childCount()
                for child_id in range(nchild):
                    child = parent.child(child_id)
                    if child.text(0) == name:
                        parent = child
                        break
                else:
                    item = QTreeWidgetItem(parent)
                    item.setText(0, name)
                    item.setExpanded(expand)
                    if idx == nfolders - 1:
                        item.setIcon(0, file_icon)
                    else:
                        item.setIcon(0, folder_icon)


class PropertyExplorer(QVBoxLayout):
    def __init__(
        self,
        parent: Optional[QWidget],
        properties: List[FGPropertyNode],
        property_root: str,
    ):
        super().__init__(parent)
        self._property_root = property_root

        self.addWidget(QLabel("Property Explorer"))
        property_tree = HierarchicalTree(
            [self.get_relative_name(p) for p in properties], ["Property", "Value"]
        )
        property_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.addWidget(property_tree)

    def get_relative_name(self, node: FGPropertyNode) -> str:
        name = node.get_fully_qualified_name()
        if name.startswith(self._property_root):
            return name[len(self._property_root) + 1 :]
        return name
