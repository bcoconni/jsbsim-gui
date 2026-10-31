# A Graphical User Interface for JSBSim
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

import time
import tkinter as tk
from tkinter import ttk
from tkinter.constants import EW, NSEW
from tkinter.messagebox import showerror
from typing import Callable, Optional

from .controller import Controller


class SimulationControls(ttk.Frame):
    REALTIME_UPDATE_INTERVAL_ms = 200
    MAX_UPDATE_TIME_s = 0.95 * REALTIME_UPDATE_INTERVAL_ms / 1000

    def __init__(
        self,
        master: tk.Widget,
        controller: Controller,
        on_update: Callable[[], None],
        on_trimmed: Callable[[], None],
        **kw,
    ):
        super().__init__(master, **kw)
        self.controller = controller
        self._on_update = on_update
        self._on_trimmed = on_trimmed
        self.update_id: Optional[str] = None
        self.initial_seconds = 0.0
        self.script_end_reached = False
        self.initialized = False
        self.bind("<Destroy>", self._on_destroy, add="+")

        self.init_button = ttk.Button(self, text="Initialize", command=self.run_ic)
        self.init_button.grid(column=0, row=0, columnspan=3, sticky=EW)
        self.trim_button = ttk.Button(self, text="Trim", command=self._trim)
        self.trim_button.grid(column=0, row=1, sticky=EW, padx=(0, 2), pady=4)
        self.trim_options = ttk.Combobox(self, values=["Full Trim", "Ground Trim"])
        self.trim_options.current(0)
        self.trim_options.grid(column=1, row=1, sticky=NSEW, padx=(2, 0), pady=4)
        self.step_button = ttk.Button(self, text="Step", command=self.step)
        self.step_button.grid(column=0, row=2, sticky=EW, padx=(0, 2))
        self.run_pause_button = ttk.Button(self, text="Run", command=self.run)
        self.run_pause_button.grid(column=1, row=2, sticky=EW, padx=(2, 0))
        self.columnconfigure(0, weight=1, uniform="controls")
        self.columnconfigure(1, weight=1, uniform="controls")
        self._set_run_state(False, False)

    @property
    def is_running(self) -> bool:
        return self.update_id is not None

    def _set_run_state(self, initialized: bool, running: bool) -> None:
        self.init_button.config(state=tk.DISABLED if initialized else tk.NORMAL)
        self.trim_button.config(state=tk.NORMAL if initialized else tk.DISABLED)
        self.trim_options.config(state="readonly" if initialized else tk.DISABLED)
        self.step_button.config(
            state=tk.NORMAL if initialized and not running else tk.DISABLED
        )
        self.run_pause_button.config(
            state=tk.NORMAL if initialized else tk.DISABLED,
            command=self.pause if running else self.run,
            text="Pause" if running else "Run",
        )

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self and self.update_id is not None:
            self.after_cancel(self.update_id)
            self.update_id = None

    def reset_for_reload(self) -> None:
        if self.is_running:
            self.pause()
        self.initial_seconds = 0.0
        self.script_end_reached = False
        self.initialized = False
        self._set_run_state(False, False)

    def run_ic(self) -> None:
        self.controller.run_ic()
        self.initialized = True
        self._set_run_state(True, False)
        self._on_update()

    def step(self) -> None:
        self.controller.run()
        self._on_update()

    def _trim(self) -> None:
        if not self.controller.trim(self.trim_options.current() + 1):
            showerror("Error", message="Trim failed")
        else:
            self._on_trimmed()

    def _update_simulation(self) -> None:
        start_time = time.time()
        actual_elapsed_time = start_time - self.initial_seconds
        sim_time = self.controller.fdm.get_sim_time()
        sim_lag_time = actual_elapsed_time - sim_time

        for _ in range(int(sim_lag_time / self.controller.dt)):
            if not self.controller.run() and not self.script_end_reached:
                self.pause()
                self.script_end_reached = True
                break
            # If the update takes too long, break the loop
            if time.time() - start_time > self.MAX_UPDATE_TIME_s:
                self.update_id = self.after(
                    self.REALTIME_UPDATE_INTERVAL_ms, self._update_simulation
                )
                break
        else:
            self.update_id = self.after(
                self.REALTIME_UPDATE_INTERVAL_ms, self._update_simulation
            )

        self._on_update()

    def pause(self) -> None:
        assert self.update_id is not None
        self.after_cancel(self.update_id)
        self.update_id = None
        self._set_run_state(self.initialized, False)

    def run(self) -> None:
        self.update_id = self.after(
            self.REALTIME_UPDATE_INTERVAL_ms, self._update_simulation
        )
        self.initial_seconds = time.time() - self.controller.fdm.get_sim_time()
        self._set_run_state(self.initialized, True)
