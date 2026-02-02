"""Tests for __main__ module."""

import subprocess
import sys
from pathlib import Path

import pytest

from ansys.common.mcp.__main__ import main


class TestMainFunction:
    """Tests for the main entry point."""

    def test_main_returns_zero(self):
        """Test that main returns 0."""
        result = main()
        assert result == 0


@pytest.mark.integration
class TestMainScriptExecution:
    """Integration test for running __main__ as a script."""

    def test_main_script_runs_and_shows_usage(self):
        """Test script runs successfully and shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )

        # Should exit successfully
        assert result.returncode == 0

        # Should output informational message about being a library
        assert "library" in result.stdout.lower()
        assert "not meant to be run directly" in result.stdout.lower()
        assert "github" in result.stdout.lower()

        # Should not produce errors
        assert result.stderr == ""
