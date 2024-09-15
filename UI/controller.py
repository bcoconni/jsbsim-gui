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
from typing import List, Optional

import jsbsim
import numpy as np
from jsbsim._jsbsim import _append_xml as append_xml
from jsbsim import FGPropertyNode

from src.property_history import PropertyHistory


class Controller:
    @staticmethod
    def get_version() -> str:
        return jsbsim.__version__

    @staticmethod
    def get_default_root_dir() -> str:
        return jsbsim.get_default_root_dir()

    def __init__(self, root_dir: str, debug_level: int = 1):
        jsbsim.FGJSBBase().debug_lvl = debug_level
        self.dt = 1.0 / 120.0
        self.filename = ""
        self.property_history = PropertyHistory([])
        self.fdm = jsbsim.FGFDMExec(root_dir)

    def load_script(self, filename: str) -> None:
        # TODO Validate the script before loading
        self.filename = filename
        script_name = os.path.relpath(filename, self.fdm.get_root_dir())
        self.fdm.load_script(script_name)
        self.property_history = PropertyHistory(self.get_property_list())

    def load_aircraft(self, filename: str) -> None:
        # TODO Validate the aircraft definition before loading
        self.filename = filename
        aircraft_name = os.path.splitext(os.path.basename(filename))[0]
        self.fdm.load_model(aircraft_name, True)
        self.property_history = PropertyHistory(self.get_property_list())

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
        return [os.path.relpath(os.path.realpath(filename), self.get_root_dir())]

    def get_input_files(self) -> List[str]:
        aircraft_path = self.fdm.get_aircraft_path()
        input_files = self.get_relative_path(self.filename)
        root = et.parse(os.path.join(self.fdm.get_root_dir(), self.filename)).getroot()

        if root.tag == "runscript":
            use_el = root.find("use")
            aircraft_name = use_el.attrib["aircraft"]
            aircraft_filename = os.path.join(
                aircraft_path, aircraft_name, append_xml(aircraft_name)
            )
            input_files += self.get_relative_path(aircraft_filename)
            IC_file = use_el.attrib["initialize"]
            input_files += self.get_relative_path(
                os.path.join(aircraft_path, aircraft_name, append_xml(IC_file))
            )

            root = et.parse(aircraft_filename).getroot()

        engine_path = self.fdm.get_engine_path()
        systems_path = self.fdm.get_systems_path()

        for include_el in root.findall(".//*[@file]"):
            filename = append_xml(include_el.attrib["file"])
            if os.path.exists(os.path.join(aircraft_path, filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "Systems", filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, "Systems", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "systems", filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, "systems", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "Engines", filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, "Engines", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "engines", filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, "engines", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "Engine", filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, "Engine", filename)
                )
            elif os.path.exists(os.path.join(aircraft_path, "engine", filename)):
                input_files += self.get_relative_path(
                    os.path.join(aircraft_path, "engine", filename)
                )
            elif os.path.exists(os.path.join(engine_path, filename)):
                input_files += self.get_relative_path(
                    os.path.join(engine_path, filename)
                )
            elif os.path.exists(os.path.join(systems_path, filename)):
                input_files += self.get_relative_path(
                    os.path.join(systems_path, filename)
                )

        if platform.system() == "Windows":
            return [name.replace("\\", "/") for name in input_files]

        return input_files

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
            return [prop.get_double_value() for prop in properties]
