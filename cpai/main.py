import os
import sys
import json
import argparse
import subprocess
import textwrap
import logging
import fnmatch
import tempfile
import re
from typing import List, Dict, Any, Optional
from .outline.cli import FunctionInfo

# Function to configure logging
def configure_logging(debug):
    if debug:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

DEFAULT_CHUNK_SIZE = 90000

DEFAULT_EXCLUDE_PATTERNS = [
    # Build and cache
    "build/", "dist/", "__pycache__/", ".cache/", "coverage/", ".next/", 
    "out/", ".nuxt/", ".output/", "*.egg-info/",
    
    # Dependencies
    "node_modules/", "venv/", ".env/", "virtualenv/",
    
    # Test files
    "test/", "tests/", "__tests__/", "**/*.test.*", "**/*.spec.*",
    
    # IDE and OS
    ".idea/", ".vscode/", ".DS_Store",
    
    # Package files
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    
    # Misc
    ".git/", "*.log", "*.md", "__init__.py", "__main__.py",
    
    # Dotfiles and dotfolders
    ".env",
    ".envrc",
    ".env.*",
    ".python-version",
    ".ruby-version",
    ".node-version"
]

CONFIG_PATTERNS = [
    "*.config.json", "package.json", "tsconfig.json", "*.config.js",
    "*.config.ts", "pyproject.toml", "setup.py", "setup.cfg",
    "requirements.txt", "Pipfile", "Pipfile.lock"
]

CORE_SOURCE_PATTERNS = {
    # JavaScript/TypeScript/React
    "src/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "app/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "pages/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "components/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "lib/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    
    # Python
    "src/": ["*.py"],
    
    # Solidity
    "contracts/": ["*.sol"],
    "interfaces/": ["*.sol"]
}

def read_config():
    logging.debug("Reading configuration")
    default_config = {
        "include": ["."],
        "exclude": DEFAULT_EXCLUDE_PATTERNS.copy(),
        "outputFile": False,
        "usePastebin": True,
        "fileExtensions": [
            ".ts", ".js", ".py", ".rs", ".sol", ".go", ".jsx", ".tsx", 
            ".css", ".scss", ".svelte", ".html", ".java", ".c", ".cpp", 
            ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".scala", ".sh"
        ],
        "chunkSize": DEFAULT_CHUNK_SIZE
    }
    try:
        with open('cpai.config.json', 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                logging.warning("Invalid JSON in config file. Using default configuration.")
                return default_config
            
            # Validate exclude patterns
            if 'exclude' in config:
                if not isinstance(config['exclude'], list):
                    logging.warning("Invalid 'exclude' in config. Using default.")
                    config.pop('exclude')
                else:
                    # Ensure all patterns are strings
                    config['exclude'] = [str(pattern) for pattern in config['exclude']]
            
            # Validate other fields and update config
            if isinstance(config.get('outputFile'), (bool, str)):
                default_config.update(config)
            else:
                logging.warning("Invalid 'outputFile' in config. Using default.")
            
            # Ensure chunkSize is an integer
            if 'chunkSize' in config:
                if isinstance(config['chunkSize'], int):
                    default_config['chunkSize'] = config['chunkSize']
                else:
                    logging.warning("Invalid 'chunkSize' in config. Using default.")
            
            return default_config
    except FileNotFoundError:
        logging.debug("Configuration file not found. Using default configuration.")
        return default_config

def parse_gitignore(gitignore_path):
    """Parse gitignore file and convert patterns to fnmatch format"""
    ignore_patterns = []
    try:
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('!'):
                        # Negation pattern - keep the negation and convert pattern
                        pattern = line[1:]  # Remove !
                        if pattern.endswith('/*'):
                            pattern = pattern[:-2]  # Remove /*
                        ignore_patterns.append(('!', pattern))
                    else:
                        # Standard pattern
                        pattern = line  # Set pattern to the original line
                        if line.endswith('/*'):
                            pattern = pattern[:-2]  # Remove /*
                        elif line.endswith('/'):
                            pattern = line[:-1]  # Remove trailing /
                        ignore_patterns.append(('', pattern))
    except FileNotFoundError:
        pass
    return ignore_patterns

def should_ignore(file_path, ignore_patterns):
    """
    Determine if a file should be ignored based on gitignore patterns.
    Returns True if file should be ignored, False otherwise.
    """
    should_exclude = False
    
    for pattern_type, pattern in ignore_patterns:
        if pattern_type == '!':  # Negation pattern
            if fnmatch.fnmatch(file_path, pattern) or \
               fnmatch.fnmatch(os.path.dirname(file_path), pattern):
                return False  # File is explicitly included
        else:  # Standard pattern
            if fnmatch.fnmatch(file_path, pattern) or \
               fnmatch.fnmatch(os.path.dirname(file_path), pattern):
                should_exclude = True
    
    return should_exclude

def get_ignore_patterns():
    ignore_patterns = []
    current_dir = os.getcwd()
    while True:
        gitignore_path = os.path.join(current_dir, '.gitignore')
        ignore_patterns.extend(parse_gitignore(gitignore_path))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return ignore_patterns

def get_files(dir, config, include_all=False, include_configs=False):
    logging.debug(f"Getting files from directory: {dir}")
    files = []
    
    exclude_patterns = config.get('exclude', DEFAULT_EXCLUDE_PATTERNS.copy())
    if not isinstance(exclude_patterns, list):
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS.copy()
    
    # Handle gitignore patterns separately
    ignore_patterns = []
    if not include_all:
        ignore_patterns = get_ignore_patterns()
        logging.debug(f"Gitignore patterns: {ignore_patterns}")
    
    include_patterns = config.get('include', ['.'])
    if not isinstance(include_patterns, list):
        include_patterns = ['.']
    
    logging.debug(f"Include patterns: {include_patterns}")
    logging.debug(f"Exclude patterns: {exclude_patterns}")
    
    for root, dirs, filenames in os.walk(dir, topdown=True):
        rel_root = os.path.relpath(root, start=os.getcwd())
        
        # Filter directories using exclude patterns
        dirs[:] = [d for d in dirs if not any(
            d == pattern.rstrip('/') or
            fnmatch.fnmatch(os.path.join(rel_root, d) + '/', pattern) or
            fnmatch.fnmatch(os.path.join(rel_root, d), pattern.rstrip('/'))
            for pattern in exclude_patterns
        )]
        
        # Skip this directory if it matches exclude patterns
        if any(
            fnmatch.fnmatch(rel_root, pattern.rstrip('/')) or
            fnmatch.fnmatch(rel_root + '/', pattern)
            for pattern in exclude_patterns
        ):
            logging.debug(f"Skipping directory: {rel_root}")
            continue
            
        # If include pattern is ".", include everything unless excluded
        # Otherwise, check if directory matches include patterns
        if "." not in include_patterns and not any(
            fnmatch.fnmatch(rel_root, pattern) or 
            fnmatch.fnmatch(f"{rel_root}/", pattern)
            for pattern in include_patterns
        ):
            logging.debug(f"Skipping directory {rel_root} - doesn't match include patterns")
            continue
            
        for filename in filenames:
            rel_path = os.path.join(rel_root, filename)
            
            # Skip files based on gitignore patterns
            if not include_all and should_ignore(rel_path, ignore_patterns):
                logging.debug(f"Skipping file {rel_path} - matches gitignore pattern")
                continue
                
            # Skip excluded files
            if not include_all and any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_patterns):
                logging.debug(f"Skipping file {rel_path} - matches exclude pattern")
                continue
                    
            # Handle config files
            is_config = any(fnmatch.fnmatch(filename, pattern) for pattern in CONFIG_PATTERNS)
            if is_config and not (include_configs or include_all):
                logging.debug(f"Skipping config file {rel_path}")
                continue
                
            # Check file extensions
            if os.path.splitext(filename)[1] in config['fileExtensions']:
                files.append(rel_path)
                logging.debug(f"Added file: {rel_path}")
            else:
                logging.debug(f"Skipping file {rel_path} - extension not in allowed list")
    
    logging.debug(f"Total files found: {len(files)}")
    return files

def extract_outline(file_path):
    """Extract function outlines from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
        return None

    functions = []
    
    # Extract classes and their methods
    class_pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)[^{]*\{'
    for match in re.finditer(class_pattern, content):
        class_name = match.group(1)
        class_start = match.start()
        
        # Get leading comment if any
        leading_comment = None
        comment_match = re.search(r'/\*\*(.*?)\*/\s*$|//\s*(.*)$', content[:class_start], re.MULTILINE | re.DOTALL)
        if comment_match:
            leading_comment = (comment_match.group(1) or comment_match.group(2)).strip()
        
        functions.append(FunctionInfo(
            name=class_name,
            signature=match.group(0).strip(),
            line_number=content[:class_start].count('\n') + 1,
            type='class',
            leading_comment=leading_comment
        ))

    # Extract standalone functions
    function_pattern = r'(?:export\s+)?(?:async\s+)?function\s*(\w+)[^{]*\{'
    for match in re.finditer(function_pattern, content):
        func_name = match.group(1)
        func_start = match.start()
        
        # Get leading comment if any
        leading_comment = None
        comment_match = re.search(r'/\*\*(.*?)\*/\s*$|//\s*(.*)$', content[:func_start], re.MULTILINE | re.DOTALL)
        if comment_match:
            leading_comment = (comment_match.group(1) or comment_match.group(2)).strip()
        
        functions.append(FunctionInfo(
            name=func_name,
            signature=match.group(0).strip(),
            line_number=content[:func_start].count('\n') + 1,
            type='function',
            leading_comment=leading_comment
        ))

    # Extract arrow functions and assignments
    arrow_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]*)\s*=>\s*[{]'
    for match in re.finditer(arrow_pattern, content):
        func_name = match.group(1)
        func_start = match.start()
        
        # Get leading comment if any
        leading_comment = None
        comment_match = re.search(r'/\*\*(.*?)\*/\s*$|//\s*(.*)$', content[:func_start], re.MULTILINE | re.DOTALL)
        if comment_match:
            leading_comment = (comment_match.group(1) or comment_match.group(2)).strip()
        
        functions.append(FunctionInfo(
            name=func_name,
            signature=match.group(0).strip(),
            line_number=content[:func_start].count('\n') + 1,
            type='function',
            leading_comment=leading_comment
        ))

    return functions

def process_file(file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single file and return its content and outline."""
    try:
        # In tree mode, we only need the outline
        if options.get('tree'):
            outline = extract_outline(file_path)
            return {'outline': outline} if outline else None
            
        # For regular mode, get both content and outline
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return {
            'content': content,
            'outline': extract_outline(file_path)
        }
        
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
        return None

def format_outline_tree(files, options):
    """Format files and their functions as a tree structure."""
    tree = {}
    
    for file_path, content in files.items():
        if not content or not content.get('outline'):
            continue
            
        parts = os.path.normpath(file_path).split(os.sep)
        current = tree
        
        # Build path in tree
        for part in parts[:-1]:
            if not part or part == '.':
                continue
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Add file node
        filename = parts[-1]
        if filename not in current:
            current[filename] = {}
            
        # Add function nodes
        functions = {}
        for func in content['outline']:
            # Only include top-level functions (no dots in name)
            if '.' not in func.name:
                # Store function name and its comment if it exists
                comment = func.leading_comment if hasattr(func, 'leading_comment') and func.leading_comment else None
                if comment:
                    # Clean up the comment - remove comment markers and extra whitespace
                    comment = ' '.join(comment.replace('/*', '').replace('*/', '').replace('//', '').split())
                functions[func.name] = comment
        
        if functions:
            current[filename] = functions
    
    return tree

def print_tree(tree, prefix='', is_last=True, skip_empty=True, output_lines=None):
    """Print a tree structure with proper indentation."""
    if not tree:
        return
        
    items = sorted(tree.items())
    if skip_empty and not items:
        return
        
    for i, (name, subtree) in enumerate(items):
        is_last_item = i == len(items) - 1
        connector = '└── ' if is_last_item else '├── '
        next_prefix = prefix + ('    ' if is_last_item else '│   ')
        
        # If subtree is a dict of function names to comments
        if isinstance(subtree, dict) and any(isinstance(v, (str, type(None))) for v in subtree.values()):
            # Add file name
            line = f"{prefix}{connector}{name}"
            if output_lines is not None:
                output_lines.append(line)
            
            # Find the longest function name for alignment
            max_len = max(len(f"{next_prefix}└── {func_name}()") for func_name in subtree.keys())
            
            # Sort functions by name
            for j, (func_name, comment) in enumerate(sorted(subtree.items())):
                is_last_func = j == len(subtree) - 1
                func_connector = '└── ' if is_last_func else '├── '
                func_line = f"{next_prefix}{func_connector}{func_name}()"
                
                # Add comment if it exists
                if comment:
                    padding = " " * (max_len - len(func_line) + 2)
                    func_line = f"{func_line}{padding}# {comment}"
                
                if output_lines is not None:
                    output_lines.append(func_line)
        else:
            # Add directory name
            line = f"{prefix}{connector}{name}"
            if output_lines is not None:
                output_lines.append(line)
            print_tree(subtree, next_prefix, is_last_item, skip_empty, output_lines)

def format_content(files, options):
    """Format content based on options."""
    logging.debug(f"Formatting content with options: {options}")
    
    if options.get('tree'):
        tree = format_outline_tree(files, options)
        output_lines = []
        print_tree(tree, output_lines=output_lines)
        return '\n'.join(output_lines)
    
    # Regular mode output
    output = "## Directory Structure\n```\n"
    dir_structure = set()
    for file in files:
        dir_structure.add(os.path.dirname(file))
    for dir in sorted(dir_structure):
        depth = len(dir.split(os.sep)) - 1
        output += "  " * depth + (os.path.basename(dir) or ".") + "/\n"
    output += "```\n\n"
    
    for file_path, file_data in files.items():
        if file_data is None or file_data.get('content') is None:
            continue
        extension = os.path.splitext(file_path)[1][1:]  # remove the dot
        output += f"\n## {file_path}\n`{extension}\n{file_data['content']}\n`\n"
    
    return output

def format_tree(files):
    """Format files into a tree structure for display"""
    tree = {}
    for file in files:
        parts = file.split(os.sep)
        current = tree
        for part in parts[:-1]:
            if not part or part == '.':
                continue
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = None
    
    return format_tree_string(tree)

def format_tree_string(tree, prefix=""):
    """Convert tree dictionary to string representation"""
    result = []
    items = sorted(tree.items())
    logging.debug(f"Processing tree items: {items}")
    
    for i, (name, subtree) in enumerate(items):
        is_last = i == len(items) - 1
        line = f"{prefix}{'└── ' if is_last else '├── '}{name}"
        logging.debug(f"Adding line: {repr(line)}")  # Use repr to see exact string content
        result.append(line)
        
        if subtree is not None:
            next_prefix = prefix + ('    ' if is_last else '│   ')
            logging.debug(f"Processing subtree for {name} with prefix: {repr(next_prefix)}")
            subtree_result = format_tree_string(subtree, next_prefix)
            if isinstance(subtree_result, list):
                result.extend(subtree_result)
            else:
                result.extend(subtree_result.split('\n'))
    
    final_result = '\n'.join(result)
    logging.debug(f"Returning result: {repr(final_result)}")
    return final_result

def write_output(content, config):
    """Write the output to clipboard or file."""
    if not content:
        return
        
    if config.get('outputFile'):
        output_file = config['outputFile']
        with open(output_file, 'w') as f:
            f.write(content)
        logging.info(f"Output written to {output_file}")
    else:
        # Copy to clipboard using pyperclip
        import pyperclip
        pyperclip.copy(content)
        if not config.get('tree'):
            logging.info("Output copied to clipboard")

def cpai(args, cli_options):
    logging.debug("Starting cpai function")
    config = read_config()
    
    # Handle additional exclude patterns from command line
    exclude_patterns = cli_options.get('exclude', [])
    if exclude_patterns:
        if not isinstance(config['exclude'], list):
            config['exclude'] = DEFAULT_EXCLUDE_PATTERNS.copy()
        config['exclude'].extend(exclude_patterns)
    
    config.update(cli_options)

    files = {}
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for file in get_files(arg, config, 
                                    include_all=cli_options.get('include_all', False),
                                    include_configs=cli_options.get('include_configs', False)):
                    files[file] = process_file(file, cli_options)
            elif os.path.isfile(arg):  # Validate file exists
                files[arg] = process_file(arg, cli_options)
            else:
                logging.warning(f"Skipping '{arg}': not found")
    else:
        for file in get_files('.', config,
                         include_all=cli_options.get('include_all', False),
                         include_configs=cli_options.get('include_configs', False)):
            files[file] = process_file(file, cli_options)

    if not files:
        logging.warning("No files found to process")
        return

    config['files'] = list(files.keys())
    content = format_content(files, cli_options)

    write_output(content, config)

def main():
    parser = argparse.ArgumentParser(description="Concatenate multiple files into a single markdown text string")
    parser.add_argument('files', nargs='*', help="Files or directories to process")
    parser.add_argument('-f', '--file', nargs='?', const=True, help="Output to file. Optionally specify filename.")
    parser.add_argument('-n', '--noclipboard', action='store_true', help="Don't copy to clipboard")
    parser.add_argument('-a', '--all', action='store_true', help="Include all files (including tests, configs, etc.)")
    parser.add_argument('-c', '--configs', action='store_true', help="Include configuration files")
    parser.add_argument('-x', '--exclude', nargs='+', help="Additional patterns to exclude")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging")
    parser.add_argument('--outline', action='store_true', help="Extract function outlines instead of full content")
    parser.add_argument('--tree', action='store_true', help="Display a tree view of the directory structure")

    try:
        args = parser.parse_args()
        configure_logging(args.debug)

        cli_options = {
            'outputFile': args.file if args.file is not None else False,
            'usePastebin': not args.noclipboard,
            'include_all': args.all,
            'include_configs': args.configs,
            'exclude': args.exclude,
            'outline': args.outline,
            'tree': args.tree
        }

        logging.debug("Starting main function")
        cpai(args.files, cli_options)
    except (KeyboardInterrupt, SystemExit):
        # Handle both KeyboardInterrupt and SystemExit
        logging.error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)