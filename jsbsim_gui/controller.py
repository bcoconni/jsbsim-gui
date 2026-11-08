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

import xml.etree.ElementTree as et
from pathlib import Path
from typing import Iterable
from xml.parsers.expat import ExpatError

import jsbsim
import numpy as np
from jsbsim import FGPropertyNode
from jsbsim._jsbsim import _append_xml as append_xml

from .property_history import PropertyHistory
from .tree_node import XMLNode, XMLNodeBuilder


def _get_included_files(root: XMLNode) -> list[tuple[XMLNode, str]]:
    included_files: list[tuple[XMLNode, str]] = []
    for node in root:
        if "file" in node.attrs:
            filename = append_xml(node.attrs["file"].text)
            included_files.append((node, filename))

    return included_files


def print_console(msg: str) -> None:
    logger = jsbsim.get_logger()
    logger.message(msg)
    logger.flush()


def _find_in_subdirs(
    root_path: Path, subdirs: Iterable[str], alternate_path: Path, filename: str
) -> Path:
    for subdir_name in subdirs:
        fullpath = root_path / subdir_name / filename
        if fullpath.exists():
            return fullpath

    fullpath = alternate_path / filename
    if fullpath.exists():
        return fullpath

    return Path()


class Controller:
    @staticmethod
    def get_version() -> str:
        return jsbsim.__version__

    @staticmethod
    def get_default_root_dir() -> Path:
        return Path(jsbsim.get_default_root_dir()).resolve()

    def __init__(self, root_dir: Path, logger: jsbsim.FGLogger):
        self._logger = logger
        self._logger_registered = False
        self.activate_logger()
        self.dt = 1.0 / 120.0
        self.filename = Path()
        self.property_history = PropertyHistory([])
        self.fdm = jsbsim.FGFDMExec(str(root_dir))
        self.fdm.set_output_path(str(Path.cwd()))

    def __del__(self):
        self.close()

    def activate_logger(self) -> None:
        jsbsim.set_logger(self._logger)
        self._logger_registered = True

    def close(self) -> None:
        if self._logger_registered:
            jsbsim.set_logger(jsbsim.DefaultLogger())
            self._logger_registered = False

    def load_script(self, filename: Path) -> bool:
        # TODO Validate the script before loading
        self.filename = filename
        script_name = self.get_relative_path(filename)
        success = self.fdm.load_script(str(script_name))
        if success:
            self.property_history = PropertyHistory(self.get_property_list())
        return success

    def load_aircraft(self, filename: Path) -> bool:
        # TODO Validate the aircraft definition before loading
        self.filename = filename
        aircraft_name = filename.stem
        success = self.fdm.load_model(aircraft_name, True)
        if success:
            self.property_history = PropertyHistory(self.get_property_list())
        return success

    def run_ic(self) -> bool:
        ret = self.fdm.run_ic()
        self.dt = self.fdm.get_delta_t()

        self.fdm.print_simulation_configuration()
        self.fdm.get_propagate().dump_state()
        print_console("\n" + "-" * 80 + "\n\n")

        ic_trim_requested = self.fdm.get_ic().trim_requested()
        if ic_trim_requested != jsbsim.TrimMode.NONE:
            trimmer = jsbsim.FGTrim(self.fdm, ic_trim_requested)
            trimmer.do_trim()

            if self.fdm.get_debug_level() > 0:
                trimmer.report()

            print_console("\n" + "-" * 80 + "\n\n")

        self.property_history.record()
        return ret

    def run(self) -> bool:
        ret = self.fdm.run()
        self.property_history.record()
        return ret

    def get_root_dir(self) -> Path:
        return Path(self.fdm.get_root_dir()).resolve()

    def get_relative_path(self, filename: Path) -> Path:
        return filename.relative_to(self.get_root_dir())

    def get_relative_name(self, name: str) -> str:
        root = self.get_property_root()
        assert root is not None
        root_name = root.get_fully_qualified_name()
        if name.startswith(root_name + "/"):
            return name[len(root_name) + 1 :]
        return name

    def get_xml_trees(self) -> Iterable[XMLNode]:
        aircraft_path = Path(self.fdm.get_aircraft_path()).resolve()
        root = XMLNodeBuilder(self.get_relative_path(self.filename), self.filename).root
        if root is None:
            return []

        parsed_files = {self.filename: root}

        if root.name == "runscript":
            for node in root:
                assert isinstance(node, XMLNode)
                if node.name == "use" and "aircraft" in node.attrs:
                    aircraft_name = node.attrs["aircraft"].text
                    break
            else:
                raise RuntimeError(f"Malformed script file: {self.filename}")

            aircraft_path = aircraft_path / aircraft_name
            fullpath = aircraft_path / append_xml(aircraft_name)
            root = XMLNodeBuilder(self.get_relative_path(fullpath), fullpath).root
            assert root is not None
            parsed_files[fullpath] = root

            IC_file = node.attrs["initialize"].text
            fullpath = aircraft_path / append_xml(IC_file)
            ic_root = XMLNodeBuilder(self.get_relative_path(fullpath), fullpath).root
            assert ic_root is not None
            parsed_files[fullpath] = ic_root
        elif root.name == "fdm_config":
            aircraft_name = self.filename.stem
            aircraft_path = aircraft_path / aircraft_name

        engine_path = Path(self.fdm.get_engine_path()).resolve()
        systems_path = Path(self.fdm.get_systems_path()).resolve()

        included_files = _get_included_files(root)

        for node, filename in included_files:
            fullpath = Path()

            if (aircraft_path / filename).exists():
                fullpath = aircraft_path / filename
            elif node.name in ("engine", "thruster"):
                subdirs = ("Engines", "engines", "Engine", "engine")
                fullpath = _find_in_subdirs(
                    aircraft_path, subdirs, engine_path, filename
                )
            elif node.name in ("system", "flight_control", "autopilot"):
                fullpath = _find_in_subdirs(
                    aircraft_path, ("Systems", "systems"), systems_path, filename
                )

            if not fullpath.root:
                raise FileNotFoundError(f"Could not find {filename}")

            if fullpath in parsed_files:
                root_include = parsed_files[fullpath]
            else:
                root_include = XMLNodeBuilder(
                    self.get_relative_path(fullpath), fullpath
                ).root
                assert root_include is not None
                parsed_files[fullpath] = root_include
                included_files.extend(_get_included_files(root_include))

            if node.name not in ("engine", "thruster"):
                parent = node.parent
                node.parent = None
                root_include.parent = parent

        return parsed_files.values()

    def get_property_root(self) -> FGPropertyNode | None:
        return self.fdm.get_property_manager().get_node()

    def get_property_list(self) -> list[FGPropertyNode]:
        pm = self.fdm.get_property_manager()
        names = [
            p.split(" ")[0]
            for p in self.fdm.query_property_catalog("").split("\n")
            if len(p) != 0
        ]
        properties = [pm.get_node(name, False) for name in names]
        return [property for property in properties if property is not None]

    def get_property_value(self, property_name: str) -> float:
        return self.fdm[property_name]

    def get_property_log(self, node: FGPropertyNode) -> np.ndarray:
        return self.property_history.get_property_history(node)

    def get_time_snapshot(
        self, time: float, properties: list[FGPropertyNode]
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
        old_history = self.property_history
        root_dir = self.fdm.get_root_dir()
        output_path = self.fdm.get_output_path()
        success = False

        self.fdm = jsbsim.FGFDMExec(root_dir)
        self.fdm.set_output_path(output_path)

        try:
            root = et.parse(self.filename).getroot()
            if root.tag == "runscript":
                success = self.load_script(self.filename)
            elif root.tag == "fdm_config":
                success = self.load_aircraft(self.filename)
        except (OSError, et.ParseError, ExpatError, RuntimeError, ValueError, KeyError):
            self.fdm = old_fdm
            self.property_history = old_history
            raise
        if not success:
            self.fdm = old_fdm
            self.property_history = old_history
        return success
