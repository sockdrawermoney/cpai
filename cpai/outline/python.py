"""Python outline extractor."""
import ast
import logging
from typing import List, Optional

from .base import FunctionInfo, OutlineExtractor

class PythonOutlineExtractor(OutlineExtractor):
    """Extract function information from Python files."""
    
    SUPPORTED_EXTENSIONS = {'.py'}
    
    def supports_file(self, filename: str) -> bool:
        """Check if this extractor supports the given filename."""
        return any(filename.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)
    
    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function information from Python content."""
        functions = []
        current_class = None
        current_path = []
        seen_names = set()
        
        def get_docstring(node) -> Optional[str]:
            """Extract docstring from a node."""
            if not (isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and 
                   ast.get_docstring(node)):
                return None
            
            # Get the docstring and clean it
            docstring = ast.get_docstring(node)
            if docstring:
                # Take first line of docstring
                first_line = docstring.split('\n')[0].strip()
                return first_line
            return None
        
        def get_full_path(name):
            """Get the full path including class name if inside a class."""
            path_parts = filter(None, current_path + [name])
            return '.'.join(path_parts)
        
        def should_include_function(name: str) -> bool:
            """Determine if a function should be included in the outline."""
            # Skip private methods and common test functions
            if (name.startswith('_') or 
                name in ('setUp', 'tearDown', 'setUpClass', 'tearDownClass')):
                return False
            return True
        
        def add_function(name: str, node):
            """Add a function to the outline."""
            if not name or not isinstance(name, str):
                return
                
            if not should_include_function(name):
                return
                
            full_name = get_full_path(name)
            if full_name in seen_names:
                return
                
            seen_names.add(full_name)
            
            # Get docstring as the comment
            leading_comment = get_docstring(node)
            
            functions.append(FunctionInfo(
                name=full_name,
                line_number=node.lineno,
                leading_comment=leading_comment
            ))
        
        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node):
                """Visit a class definition."""
                nonlocal current_class, current_path
                
                # Store previous context
                prev_class = current_class
                prev_path = current_path.copy()
                
                try:
                    current_class = node.name
                    current_path.append(current_class)
                    add_function(current_class, node)
                    
                    # Visit all child nodes
                    self.generic_visit(node)
                finally:
                    # Restore previous context
                    current_class = prev_class
                    current_path = prev_path
            
            def visit_FunctionDef(self, node):
                """Visit a function definition."""
                add_function(node.name, node)
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                """Visit an async function definition."""
                add_function(node.name, node)
                self.generic_visit(node)
        
        try:
            tree = ast.parse(content)
            visitor = Visitor()
            visitor.visit(tree)
        except Exception as e:
            logging.error(f"Failed to parse Python code: {e}")
        
        return functions
