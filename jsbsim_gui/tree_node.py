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

from xml.parsers import expat
from typing import Dict, List, Optional


class TreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children: List[TreeNode] = []
        self._parent: Optional[TreeNode] = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent) -> None:
        if self._parent:
            self._parent.children.remove(self)
        if parent:
            parent.children.append(self)
        self._parent = parent

    @property
    def path(self) -> str:
        names: List[str] = [self.name]
        parent = self._parent
        while parent:
            names.append(parent.name)
            parent = parent._parent
        return "/".join(reversed(names))

    def __iter__(self):
        yield self
        for child in self.children:
            yield from child


class XMLNode(TreeNode):
    def __init__(
        self,
        name: str,
        attrs: Dict[str, str],
        filepath: str,
        column: int,
        line: int,
    ):
        super().__init__(name)
        self.attrs = attrs
        self.filepath = filepath
        self.column = column
        self.line = line

    def __str__(self) -> str:
        attrs = [f' {name}="{value}"' for name, value in self.attrs.items()]
        return f"<{self.name}{''.join(attrs)}>"


class XMLNodeBuilder:
    def __init__(self, filename: str, fullpath: str):
        self.root: Optional[XMLNode] = None
        self._filename = filename
        self._parent: Optional[XMLNode] = None
        self._parser = expat.ParserCreate()
        self._parser.StartElementHandler = self._start_element
        self._parser.EndElementHandler = self._end_element

        with open(fullpath, "rb") as f:
            self._parser.ParseFile(f)

    def _start_element(self, name: str, attrs: Dict[str, str]) -> None:
        node = XMLNode(
            name,
            attrs,
            self._filename,
            self._parser.CurrentColumnNumber,
            self._parser.CurrentLineNumber,
        )
        node.parent = self._parent
        self._parent = node

    def _end_element(self, _: str) -> None:
        assert self._parent is not None
        self.root = self._parent
        self._parent = self._parent.parent
