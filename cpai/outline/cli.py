"""CLI extension for code outline extraction."""
import os
from typing import List

from .javascript import JavaScriptOutlineExtractor
from .base import FunctionInfo


def get_extractor_for_file(filename: str) -> JavaScriptOutlineExtractor:
    """Get the appropriate extractor for a given file."""
    extractors = [
        JavaScriptOutlineExtractor(),
        # Add more extractors here as they are implemented
    ]
    
    for extractor in extractors:
        if extractor.supports_file(filename):
            return extractor
    return None


def extract_outline(file_path: str) -> List[FunctionInfo]:
    """Extract function outlines from a file.
    
    Args:
        file_path: Path to the file to process.
        
    Returns:
        List of FunctionInfo objects containing function information.
    """
    if not os.path.isfile(file_path):
        return []

    extractor = get_extractor_for_file(file_path)
    if not extractor:
        return []

    with open(file_path, 'r') as f:
        content = f.read()

    return extractor.extract_functions(content)
