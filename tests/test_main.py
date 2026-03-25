# Copyright (C) 2025 - 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Tests for __main__ module."""

from pathlib import Path
import subprocess
import sys

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
