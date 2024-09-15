import os
import sys
import json
import argparse
import subprocess
import textwrap
import logging

# Function to configure logging
def configure_logging(debug):
    if debug:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

DEFAULT_CHUNK_SIZE = 90000

def read_config():
    logging.debug("Reading configuration")
    default_config = {
        "include": ["."],
        "exclude": ["node_modules", "dist"],
        "outputFile": False,
        "usePastebin": True,
        "fileExtensions": [".ts", ".js", ".py"],
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

def get_files(dir, config):
    logging.debug(f"Getting files from directory: {dir}")
    files = []
    for root, _, filenames in os.walk(dir):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, start=os.getcwd())
            if any(exclude in rel_path for exclude in config['exclude']):
                continue
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

def chunk_content(content, chunk_size):
    logging.debug(f"Chunking content with chunk size: {chunk_size}")
    chunks = textwrap.wrap(content, chunk_size, break_long_words=False, replace_whitespace=False)
    logging.debug(f"Number of chunks created: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        logging.debug(f"Chunk {i+1}: {chunk[:50]}...")  # Log the first 50 characters of each chunk
    try:
        separator = f"\n\n\n\n\n------ {chunk_size} character chunk split ------\n\n\n\n\n"
        result = separator.join(chunks)
        logging.debug("Chunking completed successfully")
        return result
    except KeyError as e:
        logging.error(f"KeyError during chunking: {e}", exc_info=True)
        raise

def write_output(content, config):
    logging.debug("Writing output")
    output_file = config['outputFile']
    if output_file:
        if isinstance(output_file, bool):
            output_file = 'output-cpai.md'
        with open(output_file, 'w') as f:
            f.write(content)
        logging.info(f"Output written to {output_file}")

    if config['usePastebin']:
        chunks = chunk_content(content, config['chunkSize']).split("\n\n\n\n\n------ ")
        for i, chunk in enumerate(chunks, 1):
            if i > 1:
                chunk = "------ " + chunk
            try:
                subprocess.run(['pbcopy'], input=chunk.encode('utf-8'), check=True)
                logging.info(f"Part {i} of {len(chunks)} copied to clipboard")
                if i < len(chunks):
                    input("Press Enter when ready for the next part...")
            except subprocess.CalledProcessError:
                logging.error("Failed to copy to clipboard")

def cpai(args, cli_options):
    logging.debug("Starting cpai function")
    config = read_config()
    config.update(cli_options)

    files = []
    if args:
        for arg in args:
            if os.path.isdir(arg):
                files.extend(get_files(arg, config))
            else:
                files.append(arg)
    else:
        files = get_files('.', config)

    content = format_content(files)
    chunked_content = chunk_content(content, config['chunkSize'])

    if len(content) > config['chunkSize']:
        logging.warning(f"Output size ({len(content)} characters) exceeds the chunk size ({config['chunkSize']} characters). It will be split into multiple parts.")

    write_output(chunked_content, config)

def main():
    parser = argparse.ArgumentParser(description="Concatenate multiple files into a single markdown text string")
    parser.add_argument('files', nargs='*', help="Files or directories to process")
    parser.add_argument('-f', '--file', nargs='?', const=True, help="Output to file. Optionally specify filename.")
    parser.add_argument('-n', '--noclipboard', action='store_true', help="Don't copy to clipboard")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging based on the --debug flag
    configure_logging(args.debug)

    cli_options = {
        'outputFile': args.file if args.file is not None else False,
        'usePastebin': not args.noclipboard
    }

    logging.debug("Starting main function")

    try:
        cpai(args.files, cli_options)
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)