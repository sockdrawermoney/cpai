"""Base class for language-specific outline extractors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import re


class FunctionInfo:
    """Class to store function information."""

    def __init__(self, name, line_number=None, parameters=None, args=None, leading_comment=None, 
                 is_export=False, is_default_export=False, node_type='function'):
        self.name = name
        self.line_number = line_number
        self.parameters = parameters or args  # Support both parameters and args
        self.leading_comment = leading_comment
        self.is_export = is_export
        self.is_default_export = is_default_export
        self.node_type = node_type

    @staticmethod
    def is_valid_function_name(name):
        """Check if a function name is valid."""
        if not name:
            return False

        # Skip test functions and setup/teardown methods
        if name.startswith('test_') or name in ('setUp', 'tearDown'):
            return False

        # Skip private methods
        if name.startswith('_'):
            return False

        return True


class OutlineExtractor(ABC):
    """Base class for language-specific outline extractors."""

    @abstractmethod
    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract functions from content."""
        pass

    def format_function_for_clipboard(self, func: FunctionInfo) -> str:
        """Format a single function for clipboard output."""
        return f"{func.name}"

    def format_function_for_tree(self, func: FunctionInfo) -> str:
        """Format a function for tree display.
        
        This can be overridden by language-specific extractors to customize the display.
        """
        if hasattr(func, 'parameters') and func.parameters:
            return f"{func.name}({func.parameters})"
        return f"{func.name}()"

    def format_functions_for_clipboard(self, functions: List[FunctionInfo]) -> str:
        """Format function information for clipboard output."""
        if not functions:
            return ""
        
        # Sort functions by name for consistent ordering
        functions = sorted(functions, key=lambda f: f.name)
        
        # Convert functions to signatures only
        return "\n".join(self.format_function_for_clipboard(func) for func in functions)

    @abstractmethod
    def supports_file(self, filename: str) -> bool:
        """Check if this extractor supports the given filename."""
        pass
