"""CLI extension for code outline extraction."""
import os
import pyperclip
from typing import List

from .javascript import JavaScriptOutlineExtractor
from .base import FunctionInfo, OutlineExtractor


def get_extractor_for_file(filename: str) -> OutlineExtractor:
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


def format_function_tree(functions: List[FunctionInfo], show_line_numbers: bool = False) -> str:
    """Format function information as a tree structure."""
    if not functions:
        return ""
        
    # Sort functions by name to ensure consistent ordering
    functions = sorted(functions, key=lambda f: f.name)
    
    # Build tree structure
    tree = {}
    for func in functions:
        parts = func.name.split('.')
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = func
    
    def format_node(node, prefix='', is_last=True, indent='    ') -> str:
        if isinstance(node, dict):
            # Directory node
            if not node:
                return ''
                
            items = list(node.items())
            lines = []
            
            for i, (name, child) in enumerate(items):
                is_last_item = i == len(items) - 1
                connector = '└── ' if is_last_item else '├── '
                
                child_prefix = prefix + ('    ' if is_last_item else '│   ')
                
                if isinstance(child, FunctionInfo):
                    # Function node - just show signature
                    signature = f"`{child.signature}`"
                    if show_line_numbers:
                        signature += f"  # Line {child.line_number}"
                    lines.append(f"{prefix}{connector}{signature}")
                else:
                    # Directory node
                    lines.append(f"{prefix}{connector}{name}/")
                    child_str = format_node(child, child_prefix, is_last_item)
                    if child_str:
                        lines.append(child_str)
            
            return '\n'.join(lines)
            
        else:
            # Function leaf node - just show signature
            signature = f"`{node.signature}`"
            if show_line_numbers:
                signature += f"  # Line {node.line_number}"
            return f"{prefix}└── {signature}"
    
    return format_node(tree, prefix='')


def copy_functions_to_clipboard(functions: List[FunctionInfo], extractor: OutlineExtractor) -> None:
    """Copy function information to clipboard."""
    if not functions:
        return

    # Format functions for clipboard
    clipboard_content = extractor.format_functions_for_clipboard(functions)
    
    # Copy to clipboard using pyperclip
    pyperclip.copy(clipboard_content)
