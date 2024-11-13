import os
import sys
import json
import argparse
import subprocess
import textwrap
import logging
import fnmatch

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
    
    # Misc
    ".git/", "*.log"
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
        "exclude": DEFAULT_EXCLUDE_PATTERNS,
        "outputFile": False,
        "usePastebin": True,
        "fileExtensions": [
            ".ts", ".js", ".py", ".rs", ".sol", ".go", ".jsx", ".tsx", 
            ".css", ".scss", ".svelte", ".html", ".java", ".c", ".cpp", 
            ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".scala", ".sh", 
            ".bash", ".md", ".json", ".yaml", ".yml", ".toml"
        ],
        "chunkSize": DEFAULT_CHUNK_SIZE
    }
    try:
        with open('cpai.config.json', 'r') as f:
            config = json.load(f)
            if isinstance(config.get('outputFile'), bool) or isinstance(config.get('outputFile'), str):
                default_config.update(config)
            else:
                logging.warning("Invalid 'outputFile' in config. Using default.")
            # Ensure chunkSize is an integer
            if 'chunkSize' in config and isinstance(config['chunkSize'], int):
                default_config['chunkSize'] = config['chunkSize']
            return default_config
    except FileNotFoundError:
        logging.debug("Configuration file not found. Using default configuration.")
        return default_config

def parse_gitignore(gitignore_path):
    ignore_patterns = []
    try:
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignore_patterns.append(line)
    except FileNotFoundError:
        pass
    return ignore_patterns

def should_ignore(file_path, ignore_patterns):
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

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
    ignore_patterns = [] if include_all else get_ignore_patterns()
    
    # Ensure exclude patterns is a list
    exclude_patterns = config.get('exclude', [])
    if not isinstance(exclude_patterns, list):
        exclude_patterns = []
        logging.warning("Invalid exclude patterns in config, using empty list")
    
    for root, _, filenames in os.walk(dir):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, start=os.getcwd())
            
            # Skip excluded patterns unless --all is specified
            if not include_all:
                if any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_patterns) or should_ignore(rel_path, ignore_patterns):
                    continue
                    
            # Handle config files
            is_config = any(fnmatch.fnmatch(filename, pattern) for pattern in CONFIG_PATTERNS)
            if is_config and not (include_configs or include_all):
                continue
                
            # Check file extensions
            if os.path.splitext(filename)[1] in config['fileExtensions']:
                files.append(rel_path)
                
    logging.debug(f"Found files: {files}")
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

def chunk_content(content, chunk_size, files):
    logging.debug(f"Chunking content with chunk size: {chunk_size}")
    chunks = textwrap.wrap(content, chunk_size, break_long_words=False, replace_whitespace=False)
    
    if len(chunks) > 1:
        if not files:
            logging.warning("No files to display in tree structure")
            tree = "(no files)"
        else:
            tree = format_tree(files)
            
        print("\nWarning: Content exceeds chunk size and will be split into multiple chunks.")
        print("\nIncluded files:")
        print(tree)
        print("\nTo reduce content size, you can:")
        print("1. Create a cpai.config.json file to customize inclusion/exclusion")
        print("2. Use -x/--exclude to exclude specific paths (e.g., cpai -x tests/ docs/)")
        print("3. Be more specific about which directories to process")
        print("\nPress Enter to continue...")
        input()
    
    return chunks
        print("2. Use -x/--exclude to exclude specific paths (e.g., cpai -x tests/ docs/)")
        print("3. Be more specific about which directories to process")
        print("\nPress Enter to continue...")
        input()
    
    return chunks

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
    items = list(tree.items())
    for i, (name, subtree) in enumerate(items):
        is_last = i == len(items) - 1
        result.append(prefix + ("└── " if is_last else "├── ") + name)
        if subtree is not None:
            extension = "    " if is_last else "│   "
            result.extend(format_tree_string(subtree, prefix + extension))
    return "\n".join(result)

def write_output(content, config):
    logging.debug("Writing output")
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

    if config['usePastebin']:
        chunks = chunk_content(content, config['chunkSize'], config.get('files', []))
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            if i > 1:
                chunk = "------ " + chunk
            try:
                subprocess.run(['pbcopy'], input=chunk.encode('utf-8'), check=True)
                logging.info(f"Part {i} of {total_chunks} copied to clipboard")
                if i < total_chunks:
                    input("Press Enter when ready for the next part...")
            except subprocess.CalledProcessError:
                logging.error("Failed to copy to clipboard")
            except UnicodeEncodeError:
                logging.error("Failed to encode content for clipboard")

def cpai(args, cli_options):
    logging.debug("Starting cpai function")
    config = read_config()
    
    # Handle additional exclude patterns from command line
    exclude_patterns = cli_options.get('exclude', [])
    if exclude_patterns:
        if not isinstance(config['exclude'], list):
            config['exclude'] = []
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

    if len(content) > config['chunkSize']:
        logging.warning(f"Output size ({len(content)} characters) exceeds the chunk size ({config['chunkSize']} characters). It will be split into multiple parts.")

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