"""Rust outline extractor."""
import re
import logging
from typing import List, Optional

from .base import FunctionInfo, OutlineExtractor

class RustOutlineExtractor(OutlineExtractor):
    """Extract function information from Rust files."""
    
    SUPPORTED_EXTENSIONS = {'.rs'}
    
    # Regex patterns for Rust
    STRUCT_PATTERN = r'(?:pub(?:\([^)]*\))?\s+)?struct\s+(\w+)'
    ENUM_PATTERN = r'(?:pub(?:\([^)]*\))?\s+)?enum\s+(\w+)'
    IMPL_PATTERN = r'impl(?:\s*<[^>]+>)?\s+(?:(?:dyn\s+)?[^{]+\s+for\s+)?(\w+)'
    TRAIT_PATTERN = r'(?:pub(?:\([^)]*\))?\s+)?trait\s+(\w+)'
    FUNCTION_PATTERN = r'(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:const\s+)?fn\s+(\w+)\s*[(<]'
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
        
        try:
            lines = content.splitlines()
            in_block_comment = False
            
            for line_num, line in enumerate(lines):
                # Skip empty lines and handle block comments
                line = line.strip()
                if not line:
                    continue
                    
                if '/*' in line:
                    in_block_comment = True
                if '*/' in line:
                    in_block_comment = False
                    continue
                if in_block_comment:
                    continue
                
                # Handle struct definitions
                struct_match = re.search(self.STRUCT_PATTERN, line)
                if struct_match:
                    name = struct_match.group(1)
                    if not name.startswith('_'):
                        current_type = name
                        current_path = [name]
                        if name not in seen_names:
                            seen_names.add(name)
                            functions.append(FunctionInfo(
                                name=name,
                                line_number=line_num + 1,
                                node_type='struct',
                                leading_comment=get_leading_comment(lines, line_num)
                            ))
                    continue
                
                # Handle enum definitions
                enum_match = re.search(self.ENUM_PATTERN, line)
                if enum_match:
                    name = enum_match.group(1)
                    if not name.startswith('_'):
                        current_type = name
                        current_path = [name]
                        if name not in seen_names:
                            seen_names.add(name)
                            functions.append(FunctionInfo(
                                name=name,
                                line_number=line_num + 1,
                                node_type='enum',
                                leading_comment=get_leading_comment(lines, line_num)
                            ))
                    continue
                
                # Handle trait definitions
                trait_match = re.search(self.TRAIT_PATTERN, line)
                if trait_match:
                    name = trait_match.group(1)
                    if not name.startswith('_'):
                        current_type = name
                        current_path = [name]
                        if name not in seen_names:
                            seen_names.add(name)
                            functions.append(FunctionInfo(
                                name=name,
                                line_number=line_num + 1,
                                node_type='trait',
                                leading_comment=get_leading_comment(lines, line_num)
                            ))
                    continue
                
                # Handle impl blocks
                impl_match = re.search(self.IMPL_PATTERN, line)
                if impl_match:
                    current_impl = impl_match.group(1)
                    current_path = [current_impl]
                    # Don't add impl block as a separate item
                    continue
                
                # Handle function definitions
                fn_match = re.search(self.FUNCTION_PATTERN, line)
                if fn_match:
                    name = fn_match.group(1)
                    if not name.startswith('_') or name == '__init__':
                        full_name = f"{'.'.join(current_path)}.{name}" if current_path else name
                        if full_name not in seen_names:
                            seen_names.add(full_name)
                            functions.append(FunctionInfo(
                                name=full_name,
                                line_number=line_num + 1,
                                node_type='method' if current_impl else 'function',
                                leading_comment=get_leading_comment(lines, line_num)
                            ))
        
        except Exception as e:
            logging.error(f"Error parsing Rust code: {e}")
        
        return functions
