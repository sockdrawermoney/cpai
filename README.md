# cpai (Concatenate and Paste to AI)

cpai is a command-line tool that concatenates multiple files into a single markdown text string, making it easy to paste the full context of an application into LLMs.

## Installation

   ```
   pip install git+https://github.com/sockdrawermoney/cpai.git
   ```

## Usage

Run cpai:

```
cpai [options] [file|directory...]
```

Options:
- `--tree` or `-t`: Generate a file and function tree (currently supports Javascript/TypeScript, Python, Solidity, and Rust)
- `-f [FILENAME], --file [FILENAME]`: Output to file. If FILENAME is not provided, defaults to 'output-cpai.md'
- `-n, --noclipboard`: Don't copy to clipboard
- `-a, --all`: Include all files (including tests, configs, etc.)
- `-c, --configs`: Include configuration files
- `-x PATTERN [PATTERN...], --exclude PATTERN [PATTERN...]`: Additional patterns to exclude

If no files or directories are specified, cpai will process all supported files in the current directory.

Examples:
```
# Process src/ directory but exclude specific paths
cpai src/ -x "**/*.test.js" "docs/"

# Process multiple directories but exclude specific ones
cpai src/ lib/ -x test/ docs/ "*.spec.ts"

# Process all files except tests and specific directories
cpai -a -x tests/ documentation/ "*.md"

# Process core source files (default behavior)
cpai src/

# Process all files including tests and configs
cpai src/ -a

# Process core source files and include configs
cpai src/ -c

# Process specific files, copy to clipboard only
cpai file1.py file2.js

# Output to file (output-cpai.md) and clipboard
cpai -f

# Output to custom file and clipboard
cpai -f custom_output.md

# Output to clipboard only, no file output
cpai -n

# Output to file only, no clipboard
cpai -f -n
```

## Configuration

The tool can be configured using a `cpai.config.json` file in your project root. Here's an example configuration:

```json
{
  "include": ["."],
  "exclude": [
    "**/*.min.js",
    "**/*.bundle.js",
    "**/vendor/**"
  ],
  "fileExtensions": [".js", ".py", ".ts"],
  "outputFile": false,
  "usePastebin": true,
  "chunkSize": 90000
}
```

### File Filtering

The tool uses a combination of default exclude patterns, custom exclude patterns, and include patterns to determine which files to process:

1. **Default Exclude Patterns**: A set of common patterns (like `node_modules`, `build`, `.git`, etc.) are always excluded by default.

2. **Custom Exclude Patterns**: The `exclude` field in your config is additive - any patterns you specify are added to the default excludes.

3. **Include Patterns**: The `include` field is the only way to override excludes. If a file matches an include pattern, it will be included even if it matches an exclude pattern.

For example, if you want to process files in a `tests` directory (which is excluded by default):

```json
{
  "include": ["./tests/**/*.py"]
}
```

### File Extensions

The `fileExtensions` field specifies which file types to process. If not specified, a default set of common extensions is used.

You can create your own cpai.config.json to override any of these defaults. By default, cpai will:
1. Include only core source files (excluding tests, configs, build files, etc.)
2. Look for source files in common directories (src/, app/, pages/, components/, lib/)
3. Support common file extensions for JavaScript/TypeScript, Python, Solidity, and Rust projects

Here are the default settings that cpai starts with (you can override these in your cpai.config.json):

```json
{
  "include": ["src", "lib"],
  "exclude": [
    "build/", "dist/", "__pycache__/", ".cache/", "coverage/", ".next/",
    "out/", ".nuxt/", ".output/", "*.egg-info/",
    "node_modules/", "venv/", ".env/", "virtualenv/",
    "test/", "tests/", "__tests__/", "**/*.test.*", "**/*.spec.*",
    ".idea/", ".vscode/", ".DS_Store",
    ".git/", "*.log"
  ],
  "outputFile": false,
  "usePastebin": true,
  "fileExtensions": [
    ".ts", ".js", ".py", ".rs", ".sol", ".go", ".jsx", ".tsx",
    ".css", ".scss", ".svelte", ".html", ".java", ".c", ".cpp",
    ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
    ".bash", ".md", ".json", ".yaml", ".yml", ".toml"
  ],
  "chunkSize": 90000
}
```

The `chunkSize` parameter determines the maximum number of characters in each chunk when splitting large outputs. The default is 90,000 characters.

## Output

By default, cpai will:
1. Generate a directory structure of the processed files.
2. Concatenate the content of all processed files into a single markdown string.
3. If the content exceeds the specified chunk size:
   - A warning will be displayed showing the directory structure of included files like this:
     ```
     src/
     ├── components/
     │   ├── Button.tsx
     │   └── Input.tsx
     ├── pages/
     │   ├── index.tsx
     │   └── about.tsx
     └── utils/
         └── helpers.ts
     ```
   - Suggestions will be provided for managing large outputs:
     - Creating a cpai.config.json file to customize inclusion/exclusion
     - Using the -x/--exclude option to exclude specific paths (e.g., cpai -x tests/ docs/)
     - Being more specific about which directories to process
   - When writing to file: The content will be written as a single file with chunk separators
   - When copying to clipboard: The content will be split into chunks, and the user will be prompted to press Enter before copying each chunk
4. Copy the string (or chunks) to the clipboard (on macOS, using pbcopy).

The output format is:

```markdown
## Directory Structure

directory structure here

## path/to/filename.ext
```ext
file content

------ 90000 character chunk split ------

(next chunk of content)
```

## Dependencies

cpai uses only Python standard library modules and should work on any system with Python 3.6+.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
