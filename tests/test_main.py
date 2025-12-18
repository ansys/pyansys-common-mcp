"""Integration tests for __main__ module."""

import subprocess
import sys
from pathlib import Path

import pytest

from ansys.common.mcp.__main__ import main


@pytest.mark.integration
class TestMainFunctionIntegration:
    """Integration tests for the main entry point."""
    
    def test_main_returns_zero(self):
        """Test that main returns 0."""
        result = main()
        assert result == 0
    
    def test_main_can_be_called_directly(self):
        """Test that main() can be called directly."""
        result = main()
        assert result is not None
        assert result == 0
    
    def test_main_is_callable(self):
        """Test that main is callable."""
        assert callable(main)
    
    def test_main_has_docstring(self):
        """Test that main has a docstring."""
        assert main.__doc__ is not None


@pytest.mark.integration
class TestMainScriptExecution:
    """Integration tests running __main__ as a script."""
    
    def test_main_as_script_success(self):
        """Test running __main__ as a script succeeds."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        assert result.returncode == 0
        assert len(result.stdout) > 0
    
    def test_main_script_output_content(self):
        """Test script output contains expected content."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout
        assert "ansys-common-mcp" in output
        assert "library" in output.lower()
    
    def test_main_script_no_stderr(self):
        """Test script produces no errors."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        assert result.stderr == ""


@pytest.mark.integration
class TestMainOutputContent:
    """Integration tests verifying output content."""
    
    def test_output_mentions_library(self):
        """Test that output mentions this is a library."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        assert "library" in result.stdout.lower()
    
    def test_output_mentions_not_standalone(self):
        """Test that output indicates not a standalone server."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout.lower()
        assert "not meant to be run directly" in output or "not a standalone" in output
    
    def test_output_mentions_mcp(self):
        """Test that output mentions MCP."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout
        assert "mcp" in output.lower() or "Model Context Protocol" in output
    
    def test_output_mentions_pyansys(self):
        """Test that output mentions PyAnsys."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout
        assert "PyAnsys" in output or "pyansys" in output.lower()
    
    def test_output_mentions_product_specific_servers(self):
        """Test that output references product-specific servers."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout.lower()
        assert "pymapdl" in output or "product-specific" in output
    
    def test_output_references_documentation(self):
        """Test that output includes documentation reference."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout.lower()
        assert "github" in output or "documentation" in output


@pytest.mark.integration
class TestMainOutputFormat:
    """Integration tests verifying output format."""
    
    def test_output_is_not_empty(self):
        """Test that output is non-empty."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        assert len(result.stdout) > 0
    
    def test_output_has_multiple_lines(self):
        """Test that output has multiple lines."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        lines = [l for l in result.stdout.split("\n") if l.strip()]
        assert len(lines) > 1
    
    def test_output_lines_contain_text(self):
        """Test that all output lines contain meaningful text."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        for line in result.stdout.split("\n"):
            if line.strip():  # Non-empty lines
                # Should contain at least some alphabetic characters
                assert any(c.isalpha() for c in line)
    
    def test_output_is_printable(self):
        """Test that output is printable."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        # Output should be printable or contain newlines
        assert result.stdout.isprintable() or "\n" in result.stdout


class TestMainReturnCode:
    """Integration tests for return codes."""
    
    def test_return_code_is_zero(self):
        """Test that direct call returns 0."""
        result = main()
        assert result == 0
    
    def test_return_code_is_integer(self):
        """Test that return code is an integer."""
        result = main()
        assert isinstance(result, int)
    
    def test_script_return_code_is_zero(self):
        """Test that script execution returns 0."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        assert result.returncode == 0


@pytest.mark.integration
class TestMainConsistency:
    """Integration tests for consistency."""
    
    def test_multiple_calls_same_output(self):
        """Test that multiple calls produce same output."""
        result1 = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        result2 = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        assert result1.stdout == result2.stdout
        assert result1.returncode == result2.returncode
    
    def test_function_call_consistency(self):
        """Test that function calls are consistent."""
        result1 = main()
        result2 = main()
        
        assert result1 == result2 == 0


class TestMainDocumentation:
    """Integration tests for documentation."""
    
    def test_module_has_docstring(self):
        """Test that module has docstring."""
        import ansys.common.mcp.__main__ as main_module
        
        assert main_module.__doc__ is not None
    
    def test_main_function_has_docstring(self):
        """Test that main function has docstring."""
        assert main.__doc__ is not None


@pytest.mark.integration
class TestMainGitHubReference:
    """Integration tests for GitHub reference."""
    
    def test_github_url_in_output(self):
        """Test that GitHub URL is in output."""
        result = subprocess.run(
            [sys.executable, "-m", "ansys.common.mcp.__main__"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        
        output = result.stdout.lower()
        # Should mention github
        assert "github" in output
