"""Base class for language-specific outline extractors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FunctionInfo:
    """Information about a function extracted from code."""
    name: str
    signature: str
    line_number: int
    type: str = 'function'  # 'function', 'method', 'class', etc.
    leading_comment: Optional[str] = None


class OutlineExtractor(ABC):
    """Base class for language-specific outline extractors."""

    @abstractmethod
    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function information from code content.
        
        Args:
            content: The source code content as a string.
            
        Returns:
            List of FunctionInfo objects containing function details.
        """
        pass

    @abstractmethod
    def supports_file(self, filename: str) -> bool:
        """Check if this extractor supports the given filename.
        
        Args:
            filename: Name of the file to check.
            
        Returns:
            True if this extractor can handle the file, False otherwise.
        """
        pass
