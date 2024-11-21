"""JavaScript/TypeScript outline extractor."""
import re
from typing import List, Optional
from .base import OutlineExtractor, FunctionInfo


class JavaScriptOutlineExtractor(OutlineExtractor):
    """Extract function outlines from JavaScript/TypeScript files."""

    SUPPORTED_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx'}

    # Keywords that should not be treated as function names
    IGNORED_NAMES = {
        # React Hooks
        'useState', 'useEffect', 'useContext', 'useReducer', 'useCallback', 
        'useMemo', 'useRef', 'useImperativeHandle', 'useLayoutEffect', 
        'useDebugValue', 'useQuery', 'useMutation', 'useQueryClient',
        # Common variable names that might look like functions
        'Promise', 'Error', 'Boolean', 'String', 'Number', 'Object',
        'Array', 'Date', 'RegExp', 'Map', 'Set', 'WeakMap', 'WeakSet',
        'resolve', 'reject', 'then', 'catch', 'finally',
        # Control flow
        'if', 'for', 'while', 'switch', 'try', 'catch'
    }

    # Regex patterns for different declarations
    PATTERNS = {
        'class': r'(?:export\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',
        'function': [
            # Named function declarations (including exports)
            r'(?:export\s+)?(?:async\s+)?function\s*\*?\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*{?',
            
            # Arrow functions with explicit name (const/let/var)
            r'(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*{?',
            
            # Class methods (including constructor)
            r'(?:public|private|protected|static|async|\*)*\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*{?',
        ]
    }

    def supports_file(self, filename: str) -> bool:
        """Check if this extractor supports the given filename."""
        return any(filename.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)

    def get_leading_comment(self, lines: List[str], current_line: int) -> Optional[str]:
        """Extract comment block above the current line."""
        comments = []
        line_num = current_line - 1
        
        # Skip empty lines before comment
        while line_num >= 0 and not lines[line_num].strip():
            line_num -= 1
            
        # Collect single-line comments
        while line_num >= 0:
            line = lines[line_num].strip()
            if line.startswith('//'):
                comments.insert(0, line[2:].strip())
                line_num -= 1
            else:
                break
                
        # If we found single-line comments, return them
        if comments:
            return ' '.join(comments)
            
        # Check for multi-line comment
        if line_num >= 0:
            line = lines[line_num].strip()
            if line.endswith('*/'):
                comment_lines = []
                while line_num >= 0 and not line.startswith('/*'):
                    if line.endswith('*/'):
                        line = line[:-2].strip()
                    if line.startswith('*'):
                        line = line[1:].strip()
                    if line:
                        comment_lines.insert(0, line)
                    line_num -= 1
                    line = lines[line_num].strip() if line_num >= 0 else ''
                return ' '.join(comment_lines) if comment_lines else None
                
        return None

    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function information from JavaScript/TypeScript content."""
        functions = []
        lines = content.split('\n')
        current_class = None
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('//') or stripped_line.startswith('/*'):
                continue

            # Check for class definitions
            class_match = re.search(self.PATTERNS['class'], stripped_line)
            if class_match:
                current_class = class_match.group(1)
                leading_comment = self.get_leading_comment(lines, i)
                functions.append(FunctionInfo(
                    name=current_class,
                    signature=stripped_line,
                    line_number=i + 1,
                    type='class',
                    leading_comment=leading_comment
                ))
                continue

            # Check for function definitions
            for pattern in self.PATTERNS['function']:
                match = re.search(pattern, stripped_line)
                if match:
                    name = match.group(1)
                    
                    # Skip ignored names
                    if name in self.IGNORED_NAMES:
                        continue
                        
                    # If we're in a class, prefix the name unless it's a constructor
                    if current_class and name != 'constructor':
                        full_name = f"{current_class}.{name}"
                    else:
                        full_name = name

                    leading_comment = self.get_leading_comment(lines, i)
                    functions.append(FunctionInfo(
                        name=full_name,
                        signature=stripped_line,
                        line_number=i + 1,
                        type='method' if current_class else 'function',
                        leading_comment=leading_comment
                    ))
                    break

        return functions
