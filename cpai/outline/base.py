"""Base class for language-specific outline extractors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


class FunctionInfo:
    """Information about a function."""
    
    def __init__(self, name: str, signature: str = "", line_number: int = 0, type: str = "function", leading_comment: Optional[str] = None):
        self.name = name
        self._signature = signature
        self.line_number = line_number
        self.type = type
        self._leading_comment = leading_comment

    @property
    def signature(self) -> str:
        """Get the function signature."""
        # Never return actual signature content
        return ""

    @property
    def leading_comment(self) -> Optional[str]:
        """Get the leading comment."""
        if not self._leading_comment:
            return None
        # Clean and truncate comment
        comment = ' '.join(self._leading_comment.split())
        if len(comment) > 50:
            return comment[:47] + "..."
        return comment

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name}()"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"FunctionInfo(name='{self.name}', line={self.line_number})"


class OutlineExtractor(ABC):
    """Base class for language-specific outline extractors."""

    @abstractmethod
    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract functions from content."""
        pass

    def format_function_for_clipboard(self, func: FunctionInfo) -> str:
        """Format a single function for clipboard output."""
        return f"{func.signature}"

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
        """Check if this extractor supports the given filename.
        
        Args:
            filename: Name of the file to check.
            
        Returns:
            True if this extractor can handle the file, False otherwise.
        """
        pass
