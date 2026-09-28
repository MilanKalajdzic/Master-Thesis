"""Run thesis_analysis.ipynb from top to bottom with this Python, and save it with its outputs.

    python scripts/run_notebook.py                      # rerun in place (tables and figures go to outputs/)
    python scripts/run_notebook.py --output run.ipynb   # save the executed copy elsewhere

It runs with the Python you call it with (e.g. the repo's .venv), not whichever Jupyter kernel called "python3"
happens to be registered on the machine, and always from the repo root, so the relative paths (data/, outputs/,
src/) resolve. The PAYLEV_DATA, PAYLEV_OUTDIR and PAYLEV_RW_BOOT environment variables are passed through (the
tests use them to run the notebook on fake data). Needs the dev extras: pip install -e ".[dev]".
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO / "thesis_analysis.ipynb"
KERNEL = "paylev-run"


def run(notebook=NOTEBOOK, output=None, timeout=1800):
    import nbclient
    import nbformat

    notebook, output = Path(notebook).resolve(), Path(output or notebook).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        # a throwaway kernel that runs this Python, found before any other kernel on the machine
        spec = Path(tmp) / "kernels" / KERNEL
        spec.mkdir(parents=True)
        (spec / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "paylev", "language": "python"}))
        os.environ["JUPYTER_PATH"] = tmp + os.pathsep + os.environ.get("JUPYTER_PATH", "")
        os.environ.pop("MPLBACKEND", None)   # a forced backend (e.g. Agg) would keep figures out of the notebook

        nb = nbformat.read(notebook, as_version=4)
        start = time.time()
        print(f"running {notebook.name} ...", flush=True)
        nbclient.NotebookClient(nb, timeout=timeout, kernel_name=KERNEL,
                                resources={"metadata": {"path": str(REPO)}}).execute()
        # saved as a plain Python 3 notebook, not tied to the throwaway kernel
        nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
        nbformat.write(nb, output)
        print(f"  done in {time.time() - start:.0f}s -> {output}", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--notebook", type=Path, default=NOTEBOOK)
    p.add_argument("--output", type=Path, default=None, help="where to save the executed notebook (default: in place)")
    p.add_argument("--timeout", type=int, default=1800, help="seconds per cell (default 1800)")
    args = p.parse_args()
    try:
        import nbclient  # noqa: F401
        import nbformat  # noqa: F401
    except ImportError:
        sys.exit('needs nbclient, nbformat and ipykernel: pip install -e ".[dev]"')
    run(args.notebook, args.output, args.timeout)


if __name__ == "__main__":
    main()
