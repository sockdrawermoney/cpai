"""Rust outline extractor."""
import re
import logging
from typing import List, Optional

from .base import FunctionInfo, OutlineExtractor

class RustOutlineExtractor(OutlineExtractor):
    """Extract function information from Rust files."""
    
    SUPPORTED_EXTENSIONS = {'.rs'}
    
    # Regex patterns for Rust
    STRUCT_PATTERN = r'(?:pub\s+)?struct\s+(\w+)'
    ENUM_PATTERN = r'(?:pub\s+)?enum\s+(\w+)'
    IMPL_PATTERN = r'impl(?:\s*<[^>]+>)?\s+(\w+)'
    TRAIT_PATTERN = r'(?:pub\s+)?trait\s+(\w+)'
    FUNCTION_PATTERN = r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[(<]'
    COMMENT_PATTERN = r'(?://[^\n]*|/\*(?:[^*]|\*[^/])*\*/)\s*$'
    DOC_COMMENT_PATTERN = r'///[^\n]*'
    
    def supports_file(self, filename: str) -> bool:
        """Check if this extractor supports the given filename."""
        return any(filename.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)
    
    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function information from Rust content."""
        functions = []
        current_type = None
        current_impl = None
        current_path = []
        seen_names = set()
        
        def get_leading_comment(lines: List[str], line_num: int) -> Optional[str]:
            """Extract the leading comment for a line."""
            if line_num == 0:
                return None
            
            # First try to get doc comments (///)
            doc_comments = []
            for i in range(line_num - 1, -1, -1):
                line = lines[i].strip()
                if not line:
                    continue
                doc_match = re.match(self.DOC_COMMENT_PATTERN, line)
                if doc_match:
                    comment = re.sub(r'///\s*', '', line)
                    doc_comments.insert(0, comment)
                else:
                    break
            
            if doc_comments:
                return ' '.join(doc_comments)
            
            # Fall back to regular comments
            prev_line = lines[line_num - 1].strip()
            comment_match = re.search(self.COMMENT_PATTERN, prev_line)
            if comment_match:
                comment = comment_match.group(0)
                comment = re.sub(r'//\s*|/\*|\*/|\*\s*', '', comment)
                return comment.strip()
            return None
        
        def get_full_path(name):
            """Get the full path including type/impl name."""
            path_parts = filter(None, current_path + [name])
            return '.'.join(path_parts)
        
        def should_include_function(name: str) -> bool:
            """Determine if a function should be included in the outline."""
            # Skip internal functions and common test names
            if (name.startswith('_') or
                name in ('new', 'default', 'clone', 'drop', 'as_ref', 'as_mut', 
                        'from', 'into', 'try_from', 'try_into')):
                return False
            return True
        
        try:
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Look for type definitions (struct/enum/trait)
                for pattern, type_name in [
                    (self.STRUCT_PATTERN, 'struct'),
                    (self.ENUM_PATTERN, 'enum'),
                    (self.TRAIT_PATTERN, 'trait')
                ]:
                    match = re.search(pattern, line)
                    if match:
                        name = match.group(1)
                        current_type = name
                        current_path = [name]
                        if name not in seen_names:
                            seen_names.add(name)
                            comment = get_leading_comment(lines, i)
                            functions.append(FunctionInfo(
                                name=name,
                                line_number=i + 1,
                                leading_comment=comment
                            ))
                        break
                
                # Look for impl blocks
                match = re.search(self.IMPL_PATTERN, line)
                if match:
                    name = match.group(1)
                    current_impl = name
                    current_path = [name]
                    continue
                
                # Look for functions
                match = re.search(self.FUNCTION_PATTERN, line)
                if match:
                    name = match.group(1)
                    if should_include_function(name):
                        full_name = get_full_path(name)
                        if full_name not in seen_names:
                            seen_names.add(full_name)
                            comment = get_leading_comment(lines, i)
                            functions.append(FunctionInfo(
                                name=full_name,
                                line_number=i + 1,
                                leading_comment=comment
                            ))
        
        except Exception as e:
            logging.error(f"Failed to parse Rust code: {e}")
        
        return functions
