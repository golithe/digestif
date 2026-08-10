"""
Import smoke tests.

A major-version bump of mistralai moved the `Mistral` class out of the package
root, which broke `generate_exec_summary_mistral` at import time. Nothing in the
suite imported that module, so CI stayed green for months. These tests import
every module in src/ so that a dependency reshuffling its public API fails here
instead of at 07:00 on the Raspberry Pi.
"""

import importlib
import pkgutil
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"

MODULE_NAMES = sorted(
    module.name for module in pkgutil.iter_modules([str(SRC)]) if not module.ispkg
)


def test_every_src_module_was_discovered():
    # Guards against the discovery above silently finding nothing.
    assert "main" in MODULE_NAMES
    assert "generate_exec_summary_mistral" in MODULE_NAMES


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_imports_without_credentials(module_name, monkeypatch):
    # No API keys are set: importing the pipeline must not require them.
    for variable in ("MISTRAL_API_KEY", "RESEND_API_KEY", "RESEND_FROM"):
        monkeypatch.delenv(variable, raising=False)

    importlib.import_module(module_name)
