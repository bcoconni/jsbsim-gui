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

from typing import List, Union

from jsbsim import FGPropertyNode
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
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
                    item = self.create_leaf(self, name, item_fullname)
                    item.setIcon(0, file_icon)
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
                    else:
                        item = QTreeWidgetItem(parent)
                        item.setText(0, name)
                        item.setIcon(0, folder_icon)
                        item.setFlags(Qt.ItemIsEnabled)
                        item.setExpanded(expand)
                        parent = item

    def create_leaf(
        self, parent: Union[QTreeWidget, QTreeWidgetItem], name: str, fullname: str
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        return item

    def filter_items(self, pattern: str) -> bool:
        def filter_children(parent: QTreeWidgetItem):
            success = False
            for child_id in range(parent.childCount()):
                child = parent.child(child_id)
                if pattern in child.text(0):
                    success = True
                    continue
                if child.childCount() and filter_children(child):
                    success = True
                    child.setExpanded(True)
                    continue
                child.setHidden(True)
            return success

        success = False

        for child_id in range(self.topLevelItemCount()):
            child = self.topLevelItem(child_id)
            if pattern in child.text(0):
                success = True
                continue

            if filter_children(child):
                child.setExpanded(True)
                success = True
            else:
                child.setHidden(True)

        return success

    def unfilter_items(self):
        def unfilter_children(parent: QTreeWidgetItem):
            for child_id in range(parent.childCount()):
                child = parent.child(child_id)
                if child.isHidden():
                    child.setHidden(False)
                unfilter_children(child)

        for child_id in range(self.topLevelItemCount()):
            child = self.topLevelItem(child_id)
            if child.isHidden():
                child.setHidden(False)
            unfilter_children(child)

    def collapse(self):
        def collapse_children(parent: QTreeWidgetItem):
            for child_id in range(parent.childCount()):
                child = parent.child(child_id)
                child.setExpanded(False)
                collapse_children(child)

        for child_id in range(self.topLevelItemCount()):
            child = self.topLevelItem(child_id)
            collapse_children(child)
            child.setExpanded(False)


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
        self.itemChanged.connect(self._change_property_value)

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
                item = PropertyTreeItem(parent, p, name)
                item.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
                )
                return item
        raise ValueError(f"Property {fullname} not found")

    @Slot(QTreeWidgetItem, int)
    def _change_property_value(self, item: PropertyTreeItem, column: int):
        if column == 1:
            item.node.set_double_value(float(item.text(1)))
            item.setText(1, str(item.node.get_double_value()))


class PropertyExplorer(QWidget):
    def __init__(
        self,
        properties: List[FGPropertyNode],
        property_root: str,
    ):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Property Explorer"))
        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel("Search:"))
        search_text = QLineEdit()
        search_text.textEdited.connect(self._filter)
        search_bar.addWidget(search_text)
        collapse_button = QPushButton("Collapse")
        collapse_button.clicked.connect(self._collapse)
        search_bar.addWidget(collapse_button)
        layout.addLayout(search_bar)
        self.property_tree = PropertyTree(properties, property_root)
        self.property_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.property_tree)

    @Slot(str)
    def _filter(self, pattern: str):
        self.property_tree.unfilter_items()
        if pattern:
            self.property_tree.filter_items(pattern)

    @Slot()
    def _collapse(self):
        self.property_tree.collapse()
