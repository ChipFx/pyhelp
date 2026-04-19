"""
conftest.py — pytest bootstrap for running tests inside the pyhelp repo.

WHY THIS FILE EXISTS
--------------------
When pyhelp is used as a git submodule at ``./pyhelp/`` in a host project,
the host's root is on sys.path and ``import pyhelp`` resolves to the submodule
directory naturally.  Inside this repo the directory may not be named
``pyhelp``, so that automatic resolution does not happen.

This conftest registers the repo root as the ``pyhelp`` package in
sys.modules before any test is collected, exactly mirroring the submodule
mount — without touching any import statements in source or tests.

ENVIRONMENT ISOLATION
---------------------
Any state added to the Python environment during the test session is fully
reversed when the session ends.  Specifically:

* ``sys.modules`` entries for ``pyhelp`` and ``pyhelp.*`` that were not
  present before the session are removed.

* If pyhelp was not pip-installed before the session started but becomes
  pip-installed during it (e.g. via ``pip install -e ./pyhelp``), it is
  uninstalled when the session ends.

* If pyhelp *was already* pip-installed before the session, it is left
  installed.  We do not touch what we did not put there.

This prevents a previous test run from leaving a pip-installed version of
pyhelp that silently shadows the submodule in a host project.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).parent.resolve()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _installed_pyhelp_dist() -> str | None:
    """
    Return the pip distribution name for pyhelp if it is currently installed,
    otherwise ``None``.

    Checks both ``pyhelp`` (normal install) and any editable installs that
    expose the same top-level package.
    """
    try:
        importlib.metadata.version("pyhelp")
        return "pyhelp"
    except importlib.metadata.PackageNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Snapshot environment state BEFORE anything is changed.
# This must happen at module level (i.e. before collection) so that the
# baseline is captured before any test or fixture has a chance to alter it.
# ---------------------------------------------------------------------------

_modules_before: frozenset[str] = frozenset(
    name for name in sys.modules
    if name == "pyhelp" or name.startswith("pyhelp.")
)

_pip_dist_before: str | None = _installed_pyhelp_dist()


# ---------------------------------------------------------------------------
# Register the repo root as the 'pyhelp' package so all internal imports
# (``from pyhelp.parser import ...`` etc.) resolve correctly during tests.
# This mirrors exactly what the host project sees when the submodule is
# mounted at ``./pyhelp/``.
# ---------------------------------------------------------------------------

if "pyhelp" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        name="pyhelp",
        location=_repo_root / "__init__.py",
        submodule_search_locations=[str(_repo_root)],
    )
    _module = importlib.util.module_from_spec(_spec)
    _module.__package__ = "pyhelp"
    sys.modules["pyhelp"] = _module
    _spec.loader.exec_module(_module)


# ---------------------------------------------------------------------------
# Session fixture — reverses all environment changes after the run.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def _reverse_environment_changes() -> None:
    """
    Fully reverse all pyhelp-related environment changes after the test session.

    Scoped to ``session`` and ``autouse=True`` so it wraps every run without
    requiring explicit use in individual tests.

    Teardown order:
    1. Remove ``sys.modules`` entries for ``pyhelp`` and ``pyhelp.*`` that
       were added during this session (entries present before are left alone).
    2. Uninstall pyhelp from pip if and only if it was not installed before
       this session started — protecting pre-existing installations.
    """
    yield
    # ── 1. sys.modules cleanup ──────────────────────────────────────────────
    added_modules = [
        name for name in list(sys.modules)
        if (name == "pyhelp" or name.startswith("pyhelp."))
        and name not in _modules_before
    ]
    for mod_name in added_modules:
        sys.modules.pop(mod_name, None)

    # ── 2. pip uninstall — only if we didn't find it installed beforehand ───
    if _pip_dist_before is None:
        current_dist = _installed_pyhelp_dist()
        if current_dist is not None:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", current_dist, "--yes"],
                check=True,
            )
