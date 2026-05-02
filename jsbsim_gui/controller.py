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

import os
import platform
import xml.etree.ElementTree as et
from typing import Dict, Iterator, List, Optional
from xml.parsers import expat

import jsbsim
import numpy as np
from jsbsim import FGPropertyNode
from jsbsim._jsbsim import _append_xml as append_xml

from .consoles_panel import ConsolesPanel
from .property_history import PropertyHistory


class XMLNode:
    def __init__(
        self,
        name: str,
        attrs: Dict[str, str],
        filepath: str,
        column: int,
        line: int,
    ):
        self.name = name
        self.attrs = attrs
        self.filepath = filepath
        self.column = column
        self.line = line
        self.children: List[XMLNode] = []
        self._parent: Optional[XMLNode] = None

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


class XMLNodeBuilder:
    def __init__(self, filepath: str, fullpath: str):
        self.filepath = filepath
        self.parent: Optional[XMLNode] = None
        self.root: Optional[XMLNode] = None
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element

        with open(fullpath, "rb") as f:
            self.parser.ParseFile(f)

    def start_element(self, name: str, attrs: Dict[str, str]) -> None:
        node = XMLNode(
            name,
            attrs,
            self.filepath,
            self.parser.CurrentColumnNumber,
            self.parser.CurrentLineNumber,
        )
        node.parent = self.parent
        self.parent = node

    def end_element(self, _: str) -> None:
        self.root = self.parent
        self.parent = self.parent.parent


class Controller:
    @staticmethod
    def get_version() -> str:
        return jsbsim.__version__

    @staticmethod
    def get_default_root_dir() -> str:
        return jsbsim.get_default_root_dir()

    def __init__(self, root_dir: str, consoles_panel: ConsolesPanel):
        logger = consoles_panel.get_console_logger(self.get_relative_path)
        jsbsim.set_logger(logger)
        self._logger_registered = True
        self.dt = 1.0 / 120.0
        self.filename = ""
        self.property_history = PropertyHistory([])
        self.fdm = jsbsim.FGFDMExec(root_dir)

    def __del__(self):
        self.close()

    def close(self) -> None:
        if self._logger_registered:
            jsbsim.set_logger(jsbsim.DefaultLogger())
            self._logger_registered = False

    def load_script(self, filename: str) -> bool:
        # TODO Validate the script before loading
        self.filename = filename
        script_name = os.path.relpath(filename, self.fdm.get_root_dir())
        success = self.fdm.load_script(script_name)
        if success:
            self.property_history = PropertyHistory(self.get_property_list())
        return success

    def load_aircraft(self, filename: str) -> bool:
        # TODO Validate the aircraft definition before loading
        self.filename = filename
        aircraft_name = os.path.splitext(os.path.basename(filename))[0]
        success = self.fdm.load_model(aircraft_name, True)
        if success:
            self.property_history = PropertyHistory(self.get_property_list())
        return success

    def run_ic(self) -> bool:
        ret = self.fdm.run_ic()
        self.dt = self.fdm.get_delta_t()
        self.property_history.record()
        return ret

    def run(self) -> bool:
        ret = self.fdm.run()
        self.property_history.record()
        return ret

    def get_root_dir(self) -> str:
        return os.path.realpath(self.fdm.get_root_dir())

    def get_relative_path(self, filename: str) -> str:
        path = os.path.relpath(os.path.realpath(filename), self.get_root_dir())
        if platform.system() == "Windows":
            return path.replace("\\", "/")
        return path

    def get_relative_name(self, name: str) -> str:
        root = self.get_property_root().get_fully_qualified_name()
        if name.startswith(root + "/"):
            return name[len(root) + 1 :]
        return name

    def get_xml_trees(self) -> List[XMLNode]:
        aircraft_path = self.fdm.get_aircraft_path()
        root = XMLNodeBuilder(self.get_relative_path(self.filename), self.filename).root
        xml_trees = [root]

        if root.name == "runscript":
            for node in root:
                if node.name == "use":
                    aircraft_name = node.attrs["aircraft"]
                    break
            aircraft_path = os.path.join(aircraft_path, aircraft_name)
            aircraft_filename = os.path.join(aircraft_path, append_xml(aircraft_name))
            root = XMLNodeBuilder(
                self.get_relative_path(aircraft_filename), aircraft_filename
            ).root

            IC_file = node.attrs["initialize"]
            fullpath = os.path.join(aircraft_path, append_xml(IC_file))
            xml_trees.append(
                XMLNodeBuilder(self.get_relative_path(fullpath), fullpath).root
            )
            xml_trees.append(root)
        elif root.name == "fdm_config":
            aircraft_name = os.path.splitext(os.path.basename(self.filename))[0]
            aircraft_path = os.path.join(aircraft_path, aircraft_name)

        engine_path = self.fdm.get_engine_path()
        systems_path = self.fdm.get_systems_path()

        include_files = []
        for node in root:
            if "file" in node.attrs:
                filename = append_xml(node.attrs["file"])
                include_files.append((node, filename))

        for node, filename in include_files:
            if os.path.exists(os.path.join(aircraft_path, filename)):
                fullpath = os.path.join(aircraft_path, filename)
            elif os.path.exists(os.path.join(aircraft_path, "Systems", filename)):
                fullpath = os.path.join(aircraft_path, "Systems", filename)
            elif os.path.exists(os.path.join(aircraft_path, "systems", filename)):
                fullpath = os.path.join(aircraft_path, "systems", filename)
            elif os.path.exists(os.path.join(aircraft_path, "Engines", filename)):
                fullpath = os.path.join(aircraft_path, "Engines", filename)
            elif os.path.exists(os.path.join(aircraft_path, "engines", filename)):
                fullpath = os.path.join(aircraft_path, "engines", filename)
            elif os.path.exists(os.path.join(aircraft_path, "Engine", filename)):
                fullpath = os.path.join(aircraft_path, "Engine", filename)
            elif os.path.exists(os.path.join(aircraft_path, "engine", filename)):
                fullpath = os.path.join(aircraft_path, "engine", filename)
            elif os.path.exists(os.path.join(engine_path, filename)):
                fullpath = os.path.join(engine_path, filename)
            elif os.path.exists(os.path.join(systems_path, filename)):
                fullpath = os.path.join(systems_path, filename)
            else:
                raise FileNotFoundError(f"Could not find {filename}")

            root_include = XMLNodeBuilder(
                self.get_relative_path(fullpath), fullpath
            ).root

            if node.name in ("engine", "thruster"):
                xml_trees.append(root_include)
            else:
                parent = node.parent
                node.parent = None
                root_include.parent = parent

        return xml_trees

    def get_property_root(self) -> Optional[FGPropertyNode]:
        return self.fdm.get_property_manager().get_node()

    def get_property_list(self) -> List[FGPropertyNode]:
        pm = self.fdm.get_property_manager()
        names = [
            p.split(" ")[0]
            for p in self.fdm.query_property_catalog("").split("\n")
            if len(p) != 0
        ]
        return [pm.get_node(name, False) for name in names]

    def get_property_value(self, property_name: str) -> float:
        return self.fdm[property_name]

    def get_property_log(self, node: FGPropertyNode) -> np.ndarray:
        return self.property_history.get_property_history(node)

    def get_time_snapshot(
        self, time: float, properties: List[FGPropertyNode]
    ) -> np.ndarray:
        step = int(time / self.dt)
        try:
            return self.property_history.get_time_snapshot(step, properties)
        except ValueError:
            values = np.empty(len(properties))
            for i, prop in enumerate(properties):
                values[i] = prop.get_double_value()
            return values

    def trim(self, mode: int) -> bool:
        try:
            self.fdm["simulation/do_simple_trim"] = mode
        except jsbsim.TrimFailureError:
            return False
        return True

    def reload(self) -> bool:
        old_fdm = self.fdm
        root_dir = self.fdm.get_root_dir()
        success = False

        self.fdm = jsbsim.FGFDMExec(root_dir)

        root = et.parse(self.filename).getroot()
        if root.tag == "runscript":
            success = self.load_script(self.filename)
        elif root.tag == "fdm_config":
            success = self.load_aircraft(self.filename)

        if not success:
            self.fdm = old_fdm
        return success
