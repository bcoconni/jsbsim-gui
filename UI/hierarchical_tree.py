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
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
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

        for item_fullname in sorted(items):
            hierarchy = item_fullname.split("/")
            name = hierarchy[0]
            nfolders = len(hierarchy) - 1
            for child_id in range(self.topLevelItemCount()):
                child = self.topLevelItem(child_id)
                if child.text(0) == name:
                    parent = child
                    break
            else:
                if nfolders == 0:
                    item = self.create_leaf(parent, name, item_fullname)
                    item.setIcon(0, file_icon)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    continue

                item = QTreeWidgetItem(self)
                item.setText(0, name)
                item.setIcon(0, folder_icon)
                item.setFlags(Qt.ItemIsEnabled)
                item.setExpanded(expand)
                parent = item

            for idx, name in enumerate(hierarchy[1:]):
                nchild = parent.childCount()
                for child_id in range(nchild):
                    child = parent.child(child_id)
                    if child.text(0) == name:
                        parent = child
                        break
                else:
                    if idx == nfolders - 1:
                        item = self.create_leaf(parent, name, item_fullname)
                        item.setIcon(0, file_icon)
                        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    else:
                        item = QTreeWidgetItem(parent)
                        item.setText(0, name)
                        item.setIcon(0, folder_icon)
                        item.setFlags(Qt.ItemIsEnabled)
                        item.setExpanded(expand)
                        parent = item

    def create_leaf(
        self, parent: QTreeWidgetItem, name: str, fullname: str
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        return item


class FileTree(HierarchicalTree):
    file_selected = Signal(str)

    def __init__(self, files: List[str]):
        super().__init__(files, ["Files"], True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.itemSelectionChanged.connect(self._file_selected)

    @Slot()
    def _file_selected(self):
        items = self.selectedItems()
        if not items:
            return

        item = items[0]
        name = [item.text(0)]

        while item.parent():
            item = item.parent()
            name.insert(0, item.text(0))

        self.file_selected.emit("/".join(name))


class PropertyTreeItem(QTreeWidgetItem):
    def __init__(self, parent: QTreeWidgetItem, node: FGPropertyNode, name: str):
        super().__init__(parent)
        self.node = node
        self.setText(0, name)
        self.setText(1, str(node.get_double_value()))


class PropertyTree(HierarchicalTree):
    def __init__(
        self,
        properties: List[FGPropertyNode],
        property_root: str,
    ):
        self._property_root = property_root
        self._properties = properties
        super().__init__(
            [self.get_relative_name(p) for p in properties], ["Property", "Value"]
        )

    def get_relative_name(self, node: FGPropertyNode) -> str:
        name = node.get_fully_qualified_name()
        if name.startswith(self._property_root):
            return name[len(self._property_root) + 1 :]
        return name

    def create_leaf(
        self, parent: QTreeWidgetItem, name: str, fullname: str
    ) -> QTreeWidgetItem:
        for p in self._properties:
            if self.get_relative_name(p) == fullname:
                return PropertyTreeItem(parent, p, name)


class PropertyExplorer(QWidget):
    def __init__(
        self,
        properties: List[FGPropertyNode],
        property_root: str,
    ):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Property Explorer"))
        property_tree = PropertyTree(properties, property_root)
        property_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(property_tree)
