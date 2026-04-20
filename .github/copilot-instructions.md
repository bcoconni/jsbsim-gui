# JSBSim GUI - AI Coding Agent Instructions

## Project Overview
A Tkinter-based GUI for [JSBSim](https://github.com/JSBSim-Team/jsbsim) flight dynamics simulation. The app allows users to load aircraft models/scripts, configure simulations, visualize flight data with real-time plots, and explore/modify JSBSim properties through a hierarchical tree interface.

## Architecture

### Core Components
- **`app.py`**: Main application window with menu bar and view switching (edit/run modes)
- **`controller.py`**: Central coordinator wrapping JSBSim's `FGFDMExec`, manages XML parsing, property access, and console output redirection
- **`run.py`**: Real-time simulation view with property explorer, plots, and drag-n-drop workflow
- **`source_editor.py`**: XML/source file editor with syntax highlighting and property explorer
- **`hierarchical_tree.py`**: Reusable tree widgets (`PropertyTree`, `FileTree`, `XMLTree`) with filtering/searching
- **`plots_view.py`**: Matplotlib-based plotting with interactive hover/crosshair, zoom/pan, and drag-n-drop property selection
- **`property_history.py`**: Efficient chunked storage (numpy arrays) for time-series property data
- **`plotinfo_list.py`**: Smart property naming that finds common paths to generate unique, minimal display names

### Key Design Patterns
1. **View Switching**: The main window (`App`) replaces `self.main` widget between logo → `SourceEditor` → `Run` modes
3. **Drag-n-Drop**: Abstract `DragNDropManager` pattern used for property-to-plot workflow (see `DnDProperties` in `run.py`)
4. **XML Tracking**: Custom `XMLNode` tree (built via expat parser) tracks file paths and line numbers for navigation from XML tree to source editor

## Development Workflows

### Running the Application
```bash
python -m jsbsim_gui              # Entry point is jsbsim_gui/__main__.py
python -m jsbsim_gui --root /path/to/jsbsim/data  # Override JSBSim root directory
```

By default, the app uses JSBSim's data directory from the Python library installation. For testing, aircraft/engines/scripts included with JSBSim's Python package are used—no separate data files required.

### Testing
```bash
python -m unittest discover -s tests  # Run all tests
python -m unittest tests.test_plotinfo_list  # Specific test module
```
Tests use `jsbsim.FGPropertyManager` for property node mocking. No external fixtures required.

### Dependencies
- **jsbsim** (≥1.3.0): Python bindings to JSBSim C++ library (includes aircraft/engines/scripts data for testing)
- **matplotlib**: Plotting with TkAgg backend
- **PIL/Pillow**: Logo image loading (implicit dependency)
- **Tkinter**: Ships with Python, not in requirements.txt

**Dependency Policy**: ALWAYS prefer Python standard library over PyPI packages. Do NOT add new dependencies without explicit approval. This keeps the project lightweight and reduces maintenance burden.

### Logo Assets
Logo images are managed via git submodule from `https://github.com/JSBSim-Team/jsbsim-logo.git`:
```bash
git submodule init
git submodule update
```
Logo path is hardcoded to `logo/wizard_installer/logo_JSBSIM_globe_410x429.bmp` in `app.py`.

## Project-Specific Conventions

### Code Quality Standards
- **Formatting**: All Python code MUST be formatted with [Black](https://black.readthedocs.io/). Run `black .` before committing.
- **Type Hints**: Use Python typing annotations for all functions/methods to catch type errors early. Check minimum supported Python version (3.10+) for typing compatibility—avoid newer typing features like `X | Y` union syntax.
- **No Docstrings**: This is an application, NOT a library. NEVER use docstrings (""" ... """). Instead, use clear, descriptive function and variable names that make the code self-documenting.
- **Avoid Trivial Micro-functions**: Do not decompose logic into one-line or trivial functions (e.g., `def add_one(x): return x+1`) for the sake of decomposition. Only extract functions when they provide a meaningful, reusable abstraction or significantly improve the clarity of complex logic.
- **Code Clarity**: Favor readable, straightforward code over convoluted, astute, or "clever" solutions. Simple code that's easy to understand beats smart code that's hard to maintain. Keep trivial logic inline to reduce cognitive load and prevent unnecessary jumping between small function definitions.
- **Standard Library First**: Strongly prefer `import tkinter`, `import xml.etree`, `import os`, etc. over adding new PyPI dependencies.
- **Final Review Protocol:** Once the entire task is complete and before providing your final response, you must execute `git diff` and use its output as a mandatory checklist to align your work with the following rules:
  1. **Analyze & Reconcile:** Read the diff carefully. If any change is not strictly necessary or degrades readability, you must immediately revert or fix those specific lines.
  2. **Human-Centric Review:** The primary goal is to ensure the final diff is as easy as possible for a human to review. Minimize cognitive load by keeping changes strictly scoped to the task.
  3. **Whitespace Exception:** Ignore any changes related to 'trailing spaces' removal (handled by IDE). Do not revert these.
  4. **Scope Enforcement:** If the diff shows that you have touched files or lines unrelated to the given task, revert those specific changes.
  5. **Validation:** Do not consider the task finished until the `git diff` output perfectly reflects the minimal set of changes required for the given task.

### Property Path Handling
- Always use forward slashes `/` in property paths, even on Windows (see `get_relative_path()` and `PlotInfoList`)
- Properties use fully qualified names: `node.get_fully_qualified_name()` returns absolute paths starting with `/`

### Real-Time Update Pattern
The simulation loop in `Run.update_plots()` uses:
- **200ms interval** (`REALTIME_UPDATE_INTERVAL_ms`) for UI updates
- **Batch execution** of JSBSim steps to catch up with real-time, but breaks early if processing exceeds 95% of interval
- Tracks `initial_seconds` to calculate `sim_lag_time` and maintain real-time pacing

### Matplotlib Integration Gotchas
- **Blitting for performance**: `canvas.blit()` used with animated artists (crosshair line, value labels)
- **Inverted y-axis**: `get_axes_at_coordinates()` must flip y-coordinate because Matplotlib's origin is bottom-left, Tkinter's is top-left
- Last line in each subplot axis is the **animated crosshair** (`ax.lines[-1]`), don't treat it as data

### Property Filtering and Search
- `HierarchicalTree.filter()` detaches non-matching items but stores them in `_hidden_items` for restoration
- Always call `update_visible_properties()` after search/filter/collapse operations to update property value display
- Visible properties drive the update loop—only fetch values for currently displayed items

### XML File Resolution
JSBSim uses multiple search paths (see `Controller.get_xml_trees()`):
1. Aircraft directory
2. Aircraft/Systems, Aircraft/systems
3. Aircraft/Engines, Aircraft/engines, Aircraft/Engine, Aircraft/engine
4. Shared engine_path
5. Shared systems_path

Include files must be resolved before building the full XML tree for navigation.

### Testing Patterns
- Property tests use `FGPropertyManager.get_node(path, create=True)` to build test hierarchies
- Test property naming logic with edge cases: single property, duplicate names, common path trimming
- Use `np.array_equal()` for numpy array comparisons in property history tests

## Common Tasks

### Adding a New Tree Widget
1. Subclass `SearchableTree` (provides search box and collapse button)
2. Pass lambda to create underlying `HierarchicalTree` with column definitions
3. Bind custom selection handlers with `tree.tree.bind("<<TreeviewSelect>>", ...)`
4. Example: `XMLTree` in `source_editor.py`

### Adding a New Plot Feature
1. Connect to matplotlib events via `canvas.mpl_connect(event_name, handler)`
2. Use `animated=True` for frequently updated artists (lines, text)
3. Reset bbox cache (`self.bbox = None`) when layout changes require full redraw
4. See `on_scroll()` for zoom implementation pattern

### Extending Property History
- Chunk size is 100 (`PropertyHistory.CHUNK_SIZE`)
- Add new properties during init—runtime addition not supported
- Use `get_property_history()` for full time series, `get_time_snapshot()` for single timestep

## Known Gotchas

1. **Logo path**: Hardcoded relative path `logo/wizard_installer/...` requires running from repo root
2. **Window resizing**: Main window starts non-resizable, becomes resizable after file load
3. **Trim failures**: JSBSim trim (`simulation/do_simple_trim`) raises `TrimFailureError` exceptions—must catch explicitly
4. **Property node lifetime**: JSBSim property nodes are live references; value changes reflect immediately without re-fetching
5. **Step vs Run**: `fdm.run_ic()` must be called before `fdm.run()`—UI enforces this via button state management
