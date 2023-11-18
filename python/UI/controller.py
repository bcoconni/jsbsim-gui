#
# Copyright (c) 2023 Bertrand Coconnier
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
import xml.etree.ElementTree as et
import platform

import jsbsim
from jsbsim._jsbsim import _append_xml as append_xml


class Controller:
    @staticmethod
    def get_version():
        return jsbsim.__version__

    @staticmethod
    def get_default_root_dir():
        return jsbsim.get_default_root_dir()

    def __init__(self, root_dir: str, widget):
        self.widget = widget
        with widget.stdout_to_console():
            self.fdm = jsbsim.FGFDMExec(root_dir)

    def load_script(self, filename: str) -> None:
        # TODO Validate the script before loading
        script_name = os.path.relpath(filename, self.fdm.get_root_dir())
        with self.widget.stdout_to_console():
            self.fdm.load_script(script_name)

    def load_aircraft(self, filename: str) -> None:
        # TODO Validate the aircraft definition before loading
        aircraft_name = os.path.splitext(os.path.basename(filename))[0]
        with self.widget.stdout_to_console():
            self.fdm.load_model(aircraft_name, True)

    def get_input_files(self, filename) -> list[str]:
        root_dir = self.fdm.get_root_dir()

        def relpath_filename(filename):
            return [os.path.relpath(filename, root_dir)]

        aircraft_path = self.fdm.get_aircraft_path()
        input_files = relpath_filename(filename)
        root = et.parse(os.path.join(root_dir, filename)).getroot()

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

        if platform.system() == 'Windows':
            return [name.replace("\\", "/") for name in input_files]

        return input_files

    def get_property_list(self) -> list[str]:
        return [
            p.split(" ")[0]
            for p in self.fdm.query_property_catalog("").split("\n")
            if len(p) != 0
        ]

    def get_property_value(self, property_name: str) -> float:
        return self.fdm[property_name]
