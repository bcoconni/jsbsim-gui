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
import platform
import xml.etree.ElementTree as et
from typing import List

import jsbsim
import numpy as np
from jsbsim._jsbsim import _append_xml as append_xml
from jsbsim import FGPropertyNode

from .textview import ConsoleStdoutRedirect


class Controller:
    @staticmethod
    def get_version() -> str:
        return jsbsim.__version__

    @staticmethod
    def get_default_root_dir() -> str:
        return jsbsim.get_default_root_dir()

    def __init__(self, root_dir: str, console: ConsoleStdoutRedirect):
        self._console = console
        self.dt = 1.0 / 120.0
        self.filename = ""
        self.properties: list[FGPropertyNode] = []
        self.properties_values = np.empty((0, 0))
        with console.redirect_stdout():
            self.fdm = jsbsim.FGFDMExec(root_dir)

    def load_script(self, filename: str) -> None:
        # TODO Validate the script before loading
        self.filename = filename
        script_name = os.path.relpath(filename, self.fdm.get_root_dir())
        with self._console.redirect_stdout():
            self.fdm.load_script(script_name)

    def load_aircraft(self, filename: str) -> None:
        # TODO Validate the aircraft definition before loading
        self.filename = filename
        aircraft_name = os.path.splitext(os.path.basename(filename))[0]
        with self._console.redirect_stdout():
            self.fdm.load_model(aircraft_name, True)

    def run_ic(self) -> bool:
        with self._console.redirect_stdout():
            ret = self.fdm.run_ic()
            self.dt = self.fdm.get_delta_t()
            self.log_initial_values()
            return ret

    def run(self) -> bool:
        with self._console.redirect_stdout():
            ret = self.fdm.run()
            col = np.array([[prop.get_double_value() for prop in self.properties]]).T
            self.properties_values = np.hstack((self.properties_values, col))
            return ret

    def get_input_files(self) -> List[str]:
        root_dir = self.fdm.get_root_dir()

        def relpath_filename(filename):
            return [os.path.relpath(filename, root_dir)]

        aircraft_path = self.fdm.get_aircraft_path()
        input_files = relpath_filename(self.filename)
        root = et.parse(os.path.join(root_dir, self.filename)).getroot()

        if root.tag == "runscript":
            use_el = root.find("use")
            aircraft_name = use_el.attrib["aircraft"]
            aircraft_filename = os.path.join(
                aircraft_path, aircraft_name, append_xml(aircraft_name)
            )
            input_files += relpath_filename(aircraft_filename)
            IC_file = use_el.attrib["initialize"]
            input_files += relpath_filename(
                os.path.join(aircraft_path, aircraft_name, append_xml(IC_file))
            )

            root = et.parse(aircraft_filename).getroot()
        engine_path = self.fdm.get_engine_path()
        systems_path = self.fdm.get_systems_path()

        for include_el in root.findall(".//*[@file]"):
            filename = append_xml(include_el.attrib["file"])
            if os.path.exists(os.path.join(aircraft_path, filename)):
                input_files += relpath_filename(os.path.join(aircraft_path, filename))
            elif os.path.exists(os.path.join(aircraft_path, "Systems", filename)):
                input_files += relpath_filename(
                    os.path.join(aircraft_path, "Systems", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "systems", filename)):
                input_files += relpath_filename(
                    os.path.join(aircraft_path, "systems", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "Engines", filename)):
                input_files += relpath_filename(
                    os.path.join(aircraft_path, "Engines", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "engines", filename)):
                input_files += relpath_filename(
                    os.path.join(aircraft_path, "engines", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "Engine", filename)):
                input_files += relpath_filename(
                    os.path.join(aircraft_path, "Engine", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "engine", filename)):
                input_files += relpath_filename(
                    os.path.join(aircraft_path, "engine", filename)
                )
            elif os.path.exists(os.path.join(engine_path, filename)):
                input_files += relpath_filename(os.path.join(engine_path, filename))
            elif os.path.exists(os.path.join(systems_path, filename)):
                input_files += relpath_filename(os.path.join(systems_path, filename))

        if platform.system() == "Windows":
            return [name.replace("\\", "/") for name in input_files]

        return input_files

    def get_property_list(self) -> List[jsbsim.FGPropertyNode]:
        pm = self.fdm.get_property_manager()
        names = [
            p.split(" ")[0]
            for p in self.fdm.query_property_catalog("").split("\n")
            if len(p) != 0
        ]
        return [pm.get_node(name, False) for name in names]

    def get_property_value(self, property_name: str) -> float:
        return self.fdm[property_name]

    def log_initial_values(self) -> None:
        self.properties_values = np.array(
            [[prop.get_double_value() for prop in self.properties]]
        ).T

    def log_properties(self, properties: List[jsbsim.FGPropertyNode]) -> None:
        ncol = self.properties_values.shape[1]
        nprops = len(properties)
        new_prop_values = np.full((nprops, max(ncol, 1)), np.nan)
        new_props = 0

        for prop in properties:
            if prop not in self.properties:
                self.properties.append(prop)
                new_prop_values[new_props, -1] = prop.get_double_value()
                new_props += 1

        if ncol > 0:
            if new_props > 0:
                self.properties_values = np.vstack(
                    (self.properties_values, new_prop_values[:new_props, :])
                )
        else:
            self.log_initial_values()

    def get_property_log(self, node: FGPropertyNode) -> np.ndarray:
        prop_id = self.properties.index(node)
        return self.properties_values[prop_id, :]
