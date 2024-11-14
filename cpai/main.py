import os
import sys
import json
import argparse
import subprocess
import textwrap
import logging
import fnmatch
import tempfile

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
    ".git/", "*.log", "*.md",
    
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
                            pattern = line[:-2]  # Remove /*
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

def format_content(files):
    logging.debug("Formatting content")
    output = "## Directory Structure\n```\n"
    dir_structure = set()
    for file in files:
        dir_structure.add(os.path.dirname(file))
    for dir in sorted(dir_structure):
        depth = len(dir.split(os.sep)) - 1
        output += "  " * depth + (os.path.basename(dir) or ".") + "/\n"
    output += "```\n\n"

    for file in files:
        with open(file, 'r') as f:
            content = f.read()
        extension = os.path.splitext(file)[1][1:]  # remove the dot
        output += f"\n## {file}\n```{extension}\n{content}\n```\n"
    return output

def format_tree(files):
    """Format files into a tree structure for display"""
    tree = {}
    for file in files:
        parts = file.split(os.sep)
        current = tree
        for part in parts[:-1]:
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
    logging.debug("Writing output")
    content_size = len(content)
    chunk_size = config['chunkSize']
    
    # Check content size and warn if too large
    if content_size > chunk_size:
        if not config.get('files'):
            logging.warning("No files to display in tree structure")
            tree = "(no files)"
        else:
            tree = format_tree(config['files'])
            logging.debug(f"Generated tree structure: {repr(tree)}")
            
        print(f"\nWarning: Content size ({content_size} characters) exceeds the maximum size ({chunk_size} characters).")
        print("\nIncluded files:")
        print(tree)
        print("\nTo reduce content size, you can:")
        print("1. Create a cpai.config.json file to customize inclusion/exclusion")
        print("2. Use -x/--exclude to exclude specific paths (e.g., cpai -x tests/ docs/)")
        print("3. Be more specific about which directories to process")
        
        # Only proceed with file output if requested
        if not config['outputFile']:
            print("\nContent too large for clipboard. Use -f to write to file instead.")
            return

    # Handle file output
    output_file = config['outputFile']
    if output_file:
        if isinstance(output_file, bool):
            output_file = 'output-cpai.md'
        try:
            with open(output_file, 'w') as f:
                f.write(content)
            logging.info(f"Output written to {output_file}")
        except IOError as e:
            logging.error(f"Failed to write to file {output_file}: {e}")

    # Handle clipboard output only if content is within size limit
    if config['usePastebin'] and content_size <= chunk_size:
        try:
            # Use pbcopy directly without shell=True or pipes
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(content.encode('utf-8'))
            if process.returncode == 0:
                logging.info("Content copied to clipboard")
            else:
                logging.error("Failed to copy to clipboard")
        except (subprocess.CalledProcessError, UnicodeEncodeError) as e:
            logging.error(f"Failed to copy to clipboard: {e}")

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

    files = []
    if args:
        for arg in args:
            if os.path.isdir(arg):
                files.extend(get_files(arg, config, 
                                    include_all=cli_options.get('include_all', False),
                                    include_configs=cli_options.get('include_configs', False)))
            elif os.path.isfile(arg):  # Validate file exists
                files.append(arg)
            else:
                logging.warning(f"Skipping '{arg}': not found")
    else:
        files = get_files('.', config,
                         include_all=cli_options.get('include_all', False),
                         include_configs=cli_options.get('include_configs', False))

    if not files:
        logging.warning("No files found to process")
        return

    config['files'] = files
    content = format_content(files)

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
    args = parser.parse_args()

    # Configure logging based on the --debug flag
    configure_logging(args.debug)

    cli_options = {
        'outputFile': args.file if args.file is not None else False,
        'usePastebin': not args.noclipboard,
        'include_all': args.all,
        'include_configs': args.configs,
        'exclude': args.exclude
    }

    logging.debug("Starting main function")

    try:
        cpai(args.files, cli_options)
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)