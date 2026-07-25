# A Graphical User Interface for JSBSim
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

import os
import re
import tkinter as tk
from tkinter import ttk
import xml.etree.ElementTree as et

from jsbsim import FGPropertyNode
import numpy as np
import scipy

from ..controller import Controller
from ..plotinfo_list import PlotInfo, PlotInfoList
from ..plots_view import PlotsView


class ContactsTool(tk.Toplevel):
    def __init__(self, master: tk.Tk | tk.Toplevel, controller: Controller):
        super().__init__(master)
        self.title("Contacts")

        self._contacts: dict[int, FGPropertyNode] = {}
        root = controller.get_property_root()
        assert root is not None
        self._node_inertia = root.get_node("inertia")

        for prop in controller.get_property_list():
            name = prop.get_fully_qualified_name()

            if "gear/unit" in name or "contact/unit" in name:
                m = re.match(r"^.*(?:gear|contact)/unit\[([1-9]\d*)\]", name)
                if m:
                    num = int(m.group(1))
                else:
                    num = 0

                if num in self._contacts:
                    continue

                node = root.get_node(f"gear/unit[{num}]")
                if node is None:
                    node = root.get_node(f"contact/unit[{num}]")
                    assert node is not None

                self._contacts[num] = node

        frame = ttk.Frame(self)
        stiffness_label = ttk.Label(frame, text="Stiffness (lb/ft)")
        stiffness_label.grid(column=1, row=0, sticky=tk.EW)
        damping_label = ttk.Label(frame, text="Damping (lb/ft/s)")
        damping_label.grid(column=2, row=0, sticky=tk.EW)
        compression_label = ttk.Label(frame, text="Compression (ft)")
        compression_label.grid(column=3, row=0, sticky=tk.EW)
        contact_row = 1
        xml_trees = controller.get_xml_trees()

        for tree in xml_trees:
            if tree.name != "fdm_config":
                continue

            for node in tree:
                if node.name == "ground_reactions":
                    xml_root = et.parse(
                        os.path.join(controller.get_root_dir(), node.filepath)
                    ).getroot()
                    if xml_root.tag == "ground_reactions":
                        xml_contacts = xml_root.findall("contact")
                    else:
                        xml_contacts = xml_root.findall("ground_reactions/contact")
                    assert len(xml_contacts) == len(self._contacts.keys())
                    break
            break

        self._active_contacts: list[
            tuple[FGPropertyNode, ttk.Entry, ttk.Entry, ttk.Label]
        ] = []

        for num, prop in self._contacts.items():
            wow_node = prop.get_node("WOW")
            assert wow_node is not None
            if wow_node.get_double_value() != 0:
                xml_contact = xml_contacts[num]
                name_label = ttk.Label(frame, text=xml_contact.attrib["name"])
                name_label.grid(column=0, row=contact_row, sticky=tk.W)
                stiffness_entry = ttk.Entry(frame)
                xml_spring_coeff = xml_contact.find("spring_coeff")
                if xml_spring_coeff is not None:
                    stiffness_entry.insert(0, xml_spring_coeff.text)
                stiffness_entry.grid(column=1, row=contact_row, sticky=tk.EW)

                damping_entry = ttk.Entry(frame)
                xml_damping_coeff = xml_contact.find("damping_coeff")
                if xml_damping_coeff is not None:
                    damping_entry.insert(0, xml_damping_coeff.text)
                damping_entry.grid(column=2, row=contact_row, sticky=tk.EW)

                compression_label = ttk.Label(frame, relief=tk.SUNKEN)
                compression_label.grid(column=3, row=contact_row, sticky=tk.EW)
                self._active_contacts.append(
                    (prop, stiffness_entry, damping_entry, compression_label)
                )
                contact_row += 1

        frame.pack(padx=5)
        self._plots_view = PlotsView(self, controller)
        ttk.Button(self, text="Compute", command=self._compute).pack(pady=5)

    def _compute(self) -> None:
        cg_x = self._node_inertia.get_node("cg-x-in").get_double_value()
        cg_y = self._node_inertia.get_node("cg-y-in").get_double_value()
        mass = self._node_inertia.get_node("weight-lbs").get_double_value()
        ixx = self._node_inertia.get_node("ixx-slugs_ft2").get_double_value()
        iyy = self._node_inertia.get_node("iyy-slugs_ft2").get_double_value()
        ixy = self._node_inertia.get_node("ixy-slugs_ft2").get_double_value()
        K = np.zeros((3, 3))
        C = np.zeros((3, 3))
        M = np.array([[mass, 0.0, 0.0], [0.0, iyy, ixy], [0, ixy, ixx]])
        T = np.zeros((3, 3))

        for i, contact in enumerate(self._active_contacts):
            x = contact[0].get_node("x-position").get_double_value()
            y = contact[0].get_node("y-position").get_double_value()
            k = float(contact[1].get())
            c = float(contact[2].get())
            dx = (cg_x - x) / 12.0
            dy = (cg_y - y) / 12.0
            u = np.array([1.0, dx, dy])
            K += np.array([k * u, dx * k * u, dy * k * u])
            C += np.array([c * u, dx * c * u, dy * c * u])
            T[i, :] = u

        A = np.block([[np.zeros((3, 3)), np.eye(3)], [-K, -C]])
        B = np.block([[np.eye(3), np.zeros((3, 3))], [np.zeros((3, 3)), M]])
        val, _ = scipy.linalg.eig(A, B)
        positive_imaginary_mask = np.imag(val) > 0
        eigval = val[positive_imaginary_mask]
        freq = np.imag(eigval) / (2.0 * np.pi)
        print(freq)
        x_sol = np.linalg.solve(K, [-mass, 0.0, 0.0])
        print(x_sol)

        for i, contact in enumerate(self._active_contacts):
            du = -np.dot(x_sol, T[i, :])
            contact[3].config(text=f"{du:.6f}")

        freq_range = np.arange(0, 4.0 * np.max(freq), 0.01)
        bode_amplitude = [PlotInfo(), PlotInfo(), PlotInfo()]
        bode_phase = [PlotInfo(), PlotInfo(), PlotInfo()]

        for i, bode in enumerate(bode_amplitude + bode_phase):
            bode.name = f"DOF #{i%3}"
            bode.line_style = "-"
            bode._data = np.vstack([freq_range, np.zeros(freq_range.shape)])

        for i, f in enumerate(freq_range):
            omega = 2.0 * np.pi * f
            Z = -omega * omega * M + 1j * omega * C + K
            H = T @ np.linalg.inv(Z)
            for j in range(3):
                bode_amplitude[j]._data[1, i] = np.abs(H[j, j])
                bode_phase[j]._data[1, i] = np.angle(H[j, j])

        for i in range(3):
            bode_amplitude[i]._data[1, :] = 20.0 * np.log10(
                bode_amplitude[i]._data[1, :]
            )
            bode_phase[i]._data[1, :] = np.rad2deg(bode_phase[i]._data[1, :])

        plots_list = [
            PlotInfoList(self._plots_view.controller),
            PlotInfoList(self._plots_view.controller),
        ]
        plots_list[0]._plotinfos = bode_amplitude
        plots_list[1]._plotinfos = bode_phase
        self._plots_view.plots = plots_list
        self._plots_view.initialize_canvas()
        self._plots_view.pack()
