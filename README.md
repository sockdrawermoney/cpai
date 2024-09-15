# cpai (Concatenate and Paste to AI)

cpai is a command-line tool that concatenates multiple files into a single markdown text string, making it easy to paste the full context of an application into LLMs.

## Installation

   ```
   pip install https://github.com/sockdrawermoney/cpai.git
   ```

## Usage

Run cpai:

```
cpai [options] [file|directory...]
```

Options:
- `-f [FILENAME], --file [FILENAME]`: Output to file. If FILENAME is not provided, defaults to 'output-cpai.md'.
- `-n, --noclipboard`: Don't copy to clipboard.

If no files or directories are specified, cpai will process all supported files in the current directory.

Examples:
```
# Process all files in the current directory, copy to clipboard only
cpai

# Process specific files, copy to clipboard only
cpai file1.py file2.js

# Process all files in the src and tests directories, copy to clipboard only
cpai src tests

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

You can create a `cpai.config.json` file in your project root to customize behavior:

```json
{
  "include": ["src", "tests"],
  "exclude": ["node_modules", "dist"],
  "outputFile": false,
  "usePastebin": true,
  "fileExtensions": [".py", ".js", ".ts", ".tsx"],
  "chunkSize": 90000
}
```

The `chunkSize` parameter determines the maximum number of characters in each chunk when splitting large outputs. The default is 90,000 characters.

## Output

By default, cpai will:
1. Generate a directory structure of the processed files.
2. Concatenate the content of all processed files into a single markdown string.
3. If the content exceeds the specified chunk size:
   - When writing to file: The content will be written as a single file with chunk separators.
   - When copying to clipboard: The content will be split into chunks, and the user will be prompted to press Enter before copying each chunk.
4. Copy the string (or chunks) to the clipboard (on macOS, using pbcopy).

The output format is:

```markdown
## Directory Structure
```
directory structure here
```

## path/to/filename.ext
```ext
file content
```

------ 90000 character chunk split ------

(next chunk of content)
```

## Dependencies

cpai uses only Python standard library modules and should work on any system with Python 3.6+.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
