"""JavaScript/TypeScript outline extractor."""
import esprima
import re
from typing import List, Optional, Dict, Set
import logging

from .base import FunctionInfo, OutlineExtractor

class JavaScriptOutlineExtractor(OutlineExtractor):
    """Extract function outlines from JavaScript/TypeScript files."""

    SUPPORTED_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx'}

    def supports_file(self, filename: str) -> bool:
        """Check if this extractor supports the given filename."""
        return any(filename.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)

    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function information from JavaScript/TypeScript content."""
        functions = []
        current_class = None
        current_path = []
        seen_names = set()
        
        def get_leading_comment(node) -> Optional[str]:
            """Extract the leading comment for a node."""
            if not hasattr(node, 'loc'):
                return None
            
            # Get the line number of the node
            line_number = node.loc.start.line
            
            # Find the closest comment that ends right before this node
            closest_comment = None
            for comment in getattr(node, 'leadingComments', []):
                if hasattr(comment, 'loc') and comment.loc.end.line == line_number - 1:
                    closest_comment = comment
                    break
            
            if closest_comment:
                # Clean up the comment text
                text = closest_comment.value.strip()
                # Remove common comment markers and normalize whitespace
                text = re.sub(r'\/\*|\*\/|\/\/|\*', '', text)
                return ' '.join(text.split())
            return None

        def get_full_path(name):
            # Filter out empty strings and join with dots
            path_parts = filter(None, current_path + [name])
            return '.'.join(path_parts)

        def add_function(name: str, node):
            """Helper to add function while avoiding duplicates"""
            if not name or not isinstance(name, str):
                return
                
            # Skip internal implementation details and common patterns
            if (name.startswith('_') or 
                name.startswith('use') or  # Skip all React hooks
                name in ('getState', 'getContext', 'send', 'transition', 'handleError', 'cleanup',
                        'componentDidMount', 'componentDidUpdate', 'componentWillUnmount', 'render',
                        'mutate', 'mutateAsync', 'reset', 'onMutate', 'onError', 'onSettled', 'onSuccess',
                        'queryFn', 'mutationFn', 'backoff', 'shouldRetry')):
                return
                
            full_name = get_full_path(name)
            if full_name in seen_names:
                return
                
            seen_names.add(full_name)
            
            # Get the leading comment if available
            leading_comment = get_leading_comment(node)
            
            functions.append(FunctionInfo(
                name=full_name,
                line_number=node.loc.start.line if hasattr(node, 'loc') else 0,
                leading_comment=leading_comment
            ))

        try:
            # Parse the content with comments
            ast = esprima.parseScript(content, {'comment': True, 'loc': True, 'jsx': True})
            
            def visit_node(node, parent=None):
                nonlocal current_class, current_path
                
                # Store previous context
                prev_class = current_class
                prev_path = current_path.copy()
                
                try:
                    if node.type == 'ClassDeclaration':
                        if hasattr(node, 'id') and hasattr(node.id, 'name'):
                            current_class = node.id.name
                            current_path.append(current_class)
                            add_function(current_class, node)
                    
                    elif node.type == 'MethodDefinition':
                        if hasattr(node, 'key') and hasattr(node.key, 'name'):
                            name = node.key.name
                            if current_class:
                                current_path.append(name)
                            add_function(name, node)
                    
                    elif node.type == 'FunctionDeclaration':
                        if hasattr(node, 'id') and hasattr(node.id, 'name'):
                            name = node.id.name
                            current_path.append(name)
                            add_function(name, node)
                    
                    elif node.type == 'VariableDeclaration':
                        for declarator in node.declarations:
                            if (declarator.init and 
                                declarator.init.type in ('ArrowFunctionExpression', 'FunctionExpression') and
                                hasattr(declarator, 'id') and 
                                hasattr(declarator.id, 'name')):
                                name = declarator.id.name
                                current_path.append(name)
                                add_function(name, declarator)
                    
                    # Visit children
                    for key, value in vars(node).items():
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict) and item.get('type'):
                                    visit_node(item, node)
                        elif isinstance(value, dict) and value.get('type'):
                            visit_node(value, node)
                
                finally:
                    # Restore previous context
                    current_class = prev_class
                    current_path = prev_path
            
            # Start the traversal
            visit_node(ast)
            
        except Exception as e:
            logging.error(f"Failed to parse JavaScript/TypeScript: {e}")
        
        return functions

    def format_function_for_clipboard(self, func: FunctionInfo) -> str:
        """Format a single function for clipboard output."""
        return f"{func.name}"

    def format_functions_for_clipboard(self, functions: List[FunctionInfo]) -> str:
        """Format function information for clipboard output."""
        if not functions:
            return ""
        
        # Sort functions by name for consistent ordering
        functions = sorted(functions, key=lambda f: f.name)
        
        # Convert functions to signatures only
        return "\n".join(self.format_function_for_clipboard(func) for func in functions)
