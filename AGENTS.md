# Repository Guidelines

## Project Structure & Module Organization
Core simulation logic lives at the repository root:
- `sim.py`: main entry point for parsing `.sim` inputs and running frequency sweeps.
- `node.py`: signal-flow node model and propagation behavior.
- `element/`: element classes, ports, utilities, and R/L/C library implementations.
- `schematic/`: netlist parsing and schematic-to-network translation.
- `sim_files/`: sample inputs (`lpf.sim`, `bpf.sim`) and generated outputs (`.s2p`, `.plt`, `.png`).
- `plot1.sh`, `plot2.sh`, and `sim_files/plot.sh`: gnuplot wrappers for visualization.

## Build, Test, and Development Commands
This project does not use a build system; run scripts directly.
- `python sim.py`  
  Runs demo mode (defaults to low-pass filter example).
- `python sim.py sim_files/lpf.sim`  
  Runs a specific simulation input file.
- `pypy sim.py sim_files/bpf.sim`  
  Optional faster runtime for larger sweeps.
- `sh sim_files/plot.sh sim_files/lpf.plt`  
  Generates `output.png` from simulation plot data (requires `gnuplot`).

## Coding Style & Naming Conventions
- Use Python with 4-space indentation; avoid tabs.
- Follow existing module style: `snake_case` for functions/variables, `CapWords` for classes, and short lowercase package names.
- Preserve existing public names and flow-map conventions (for example `_flow_map`, `_S`, `node_nos`) to avoid behavioral regressions.
- Keep functions focused; add brief docstrings for non-obvious logic.

## Testing Guidelines
There is no formal automated test suite yet.
- Validate changes by running at least one known input:
  - `python sim.py sim_files/lpf.sim`
  - `python sim.py sim_files/bpf.sim`
- Confirm both `.s2p` and `.plt` files are produced and plot output renders via gnuplot.
- For parser or element changes, compare terminal summaries and output files against baseline behavior.

## Commit & Pull Request Guidelines
Git history shows short, imperative messages (for example `Update README.md`, `Create LICENSE`).
- Prefer concise imperative commit subjects: `fix netlist node parsing`.
- Keep commits focused to one logical change.
- PRs should include:
  - What changed and why.
  - How to run/verify locally (exact command lines).
  - Sample output notes or screenshots when plot behavior changes.
