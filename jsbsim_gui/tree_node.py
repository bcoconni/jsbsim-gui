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

import re
from dataclasses import dataclass
from xml.parsers import expat
from typing import Dict, List, Optional

_XML_TAG_PATTERN = re.compile(rb"""<(?:[^>"']|"[^"]*"|'[^']*')*>""")
_XML_ATTRIBUTE_PATTERN = re.compile(rb"""\s+([^\s=/>]+)\s*=\s*(['"])(.*?)\2""", re.S)


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


@dataclass
class TextRegion:
    text: str = ""
    column: int = -1
    line: int = -1


class XMLNode(TreeNode):
    def __init__(
        self,
        name: str,
        attrs: Dict[str, TextRegion],
        filepath: str,
        column: int,
        line: int,
    ):
        super().__init__(name)
        self.attrs = attrs
        self.filepath = filepath
        self.column = column
        self.line = line
        self.data: List[TextRegion] = []

    def __str__(self) -> str:
        attrs = [f' {name}="{value.text}"' for name, value in self.attrs.items()]
        return f"<{self.name}{''.join(attrs)}>"


class XMLNodeBuilder:
    def __init__(self, filename: str, fullpath: str):
        self.root: Optional[XMLNode] = None
        self._filename = filename
        self._parent: Optional[XMLNode] = None
        self._parser = expat.ParserCreate()
        self._parser.StartElementHandler = self._start_element
        self._parser.CharacterDataHandler = self._character_data
        self._parser.EndElementHandler = self._end_element

        with open(fullpath, "rb") as f:
            self._source = f.read()

        self._parser.Parse(self._source, True)

    def _start_element(self, name: str, attrs: Dict[str, str]) -> None:
        start_index = self._parser.CurrentByteIndex
        column = self._parser.CurrentColumnNumber
        line = self._parser.CurrentLineNumber
        attr_regions = {
            name: self._get_attribute_value_position(
                name, TextRegion(value, column, line), start_index
            )
            for name, value in attrs.items()
        }
        node = XMLNode(name, attr_regions, self._filename, column, line)
        node.parent = self._parent
        self._parent = node

    def _character_data(self, data: str) -> None:
        node = self._parent
        if node is not None:
            text = data.replace("\r\n", "\n").replace("\r", "\n").rstrip(" \t\n")
            region = TextRegion(
                text, self._parser.CurrentColumnNumber, self._parser.CurrentLineNumber
            )
            node.data.append(region)

    def _end_element(self, _: str) -> None:
        assert self._parent is not None
        grand_parent = self._parent.parent
        assert grand_parent is None or isinstance(grand_parent, XMLNode)
        self.root = self._parent
        self._parent = grand_parent

    def _get_attribute_value_position(
        self, name: str, attr: TextRegion, start_index: int
    ) -> TextRegion:
        tag_match = _XML_TAG_PATTERN.match(self._source, start_index)
        if tag_match is None:
            raise ValueError(f"Could not find the opening tag for attribute {name!r}")

        tag = tag_match.group()
        value_start = None
        for match in _XML_ATTRIBUTE_PATTERN.finditer(tag):
            if match.group(1).decode("utf-8") == name:
                value_start = match.start(3)
                break

        if value_start is None:
            raise ValueError(f"Could not locate attribute {name!r} in its opening tag")

        prefix = bytes(tag[:value_start]).decode("utf-8")
        prefix = prefix.replace("\r\n", "\n").replace("\r", "\n")
        lines = prefix.split("\n")
        line = attr.line
        if len(lines) == 1:
            column = attr.column + len(prefix)
        else:
            column = len(lines[-1])
            line += len(lines) - 1

        return TextRegion(attr.text, column, line)
