# A Graphical User Interface for JSBSim
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

import argparse
from .app import App
from .controller import Controller


def run():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--version", action="version", version=f"JSBSim UI {Controller.get_version()}"
    )
    parser.add_argument(
        "--root",
        metavar="<path>",
        help="specifies the JSBSim root directory (where aircraft/, engine/, etc. reside)",
    )
    parser.add_argument(
        "--model", metavar="<aircraft_name>", help="load an aircraft model"
    )
    parser.add_argument("--script", metavar="<script_name>", help="load a script")
    args = parser.parse_args()

    app = App(args.root)

    if args.model:
        app.load_model_from_cmdline(args.model)
    elif args.script:
        app.load_script_from_cmdline(args.script)
    else:
        app.display_logo()

    app.mainloop()


if __name__ == "__main__":
    run()
