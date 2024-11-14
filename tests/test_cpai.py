import unittest
import os
import tempfile
import shutil
import json
import argparse
import logging
import subprocess
from unittest.mock import patch, MagicMock
from cpai.main import (
    read_config,
    get_files,
    format_content,
    format_tree,
    parse_gitignore,
    should_ignore,
    write_output,
    cpai,
    main,
    configure_logging,
    DEFAULT_EXCLUDE_PATTERNS,
    CONFIG_PATTERNS,
    DEFAULT_CHUNK_SIZE
)

class TestCPAI(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create test directory structure
        os.makedirs(os.path.join(self.test_dir, 'src'))
        os.makedirs(os.path.join(self.test_dir, 'tests'))
        os.makedirs(os.path.join(self.test_dir, 'node_modules'))
        os.makedirs(os.path.join(self.test_dir, 'config'))
        
        # Create test files
        self.create_test_files()
        
        # Change to test directory
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def create_test_files(self):
        # Source files
        with open(os.path.join(self.test_dir, 'src', 'main.py'), 'w') as f:
            f.write('def main():\n    pass')
        with open(os.path.join(self.test_dir, 'src', 'utils.py'), 'w') as f:
            f.write('def util():\n    pass')
            
        # Test files
        with open(os.path.join(self.test_dir, 'tests', 'test_main.py'), 'w') as f:
            f.write('def test_main():\n    pass')
            
        # Config files
        with open(os.path.join(self.test_dir, 'config', 'settings.json'), 'w') as f:
            f.write('{"setting": "value"}')

    def tearDown(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_read_config_with_custom_config(self):
        """Test reading custom configuration file"""
        config_data = {
            "include": ["src"],
            "fileExtensions": [".py"],
            "chunkSize": 50000,
            "outputFile": True
        }
        with open('cpai.config.json', 'w') as f:
            json.dump(config_data, f)
        
        config = read_config()
        self.assertEqual(config['fileExtensions'], [".py"])
        self.assertEqual(config['chunkSize'], 50000)
        # Don't test include as it gets merged with defaults

    def test_read_config_with_invalid_config(self):
        """Test reading invalid configuration file"""
        with open('cpai.config.json', 'w') as f:
            f.write('invalid json')
        
        # Should return default config when JSON is invalid
        config = read_config()
        self.assertIn('include', config)
        self.assertIn('exclude', config)
        self.assertEqual(config['include'], ['.'])  # Check default value

    def test_write_output_to_file(self):
        """Test writing output to file"""
        config = {
            'outputFile': 'test_output.md',
            'usePastebin': False,
            'chunkSize': 1000,
            'files': ['src/main.py']
        }
        content = "Test content"
        
        write_output(content, config)
        
        self.assertTrue(os.path.exists('test_output.md'))
        with open('test_output.md', 'r') as f:
            self.assertEqual(f.read(), content)

    @patch('subprocess.Popen')
    def test_write_output_to_clipboard(self, mock_popen):
        """Test writing output to clipboard"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        config = {
            'outputFile': False,
            'usePastebin': True,
            'chunkSize': 1000,
            'files': ['src/main.py']
        }
        content = "Test content"
        
        write_output(content, config)
        
        mock_popen.assert_called_once_with(['pbcopy'], stdin=subprocess.PIPE)
        mock_process.communicate.assert_called_once_with(content.encode('utf-8'))

    def test_cpai_with_directory(self):
        """Test cpai function with directory input"""
        cli_options = {
            'outputFile': False,
            'usePastebin': False,
            'include_all': False,
            'include_configs': False
        }
        
        with patch('cpai.main.write_output') as mock_write:
            cpai(['src'], cli_options)
            mock_write.assert_called_once()
            # Verify that only Python files from src/ were processed
            self.assertEqual(len(mock_write.call_args[0][1]['files']), 2)

    def test_cpai_with_specific_files(self):
        """Test cpai function with specific file inputs"""
        cli_options = {
            'outputFile': False,
            'usePastebin': False
        }
        
        with patch('cpai.main.write_output') as mock_write:
            cpai(['src/main.py'], cli_options)
            mock_write.assert_called_once()
            self.assertEqual(len(mock_write.call_args[0][1]['files']), 1)

    def test_main_function_args(self):
        """Test main function argument parsing"""
        test_args = ['src/', '-f', 'output.md', '--debug']
        with patch('sys.argv', ['cpai'] + test_args):
            with patch('cpai.main.cpai') as mock_cpai:
                main()
                mock_cpai.assert_called_once()
                cli_options = mock_cpai.call_args[0][1]
                self.assertEqual(cli_options['outputFile'], 'output.md')

    def test_configure_logging(self):
        """Test logging configuration"""
        with self.assertLogs(level='DEBUG') as log:
            configure_logging(True)
            logging.debug("Test debug message")
            self.assertIn("DEBUG:root:Test debug message", log.output[0])

    def test_get_files_with_custom_extensions(self):
        """Test file collection with custom file extensions"""
        config = {
            'include': ['.'],
            'exclude': [],
            'fileExtensions': ['.json']
        }
        files = get_files('.', config, include_all=True)
        self.assertTrue(any('settings.json' in f for f in files))

    def test_format_tree_complex(self):
        """Test tree formatting with complex directory structure"""
        files = [
            'src/main.py',
            'src/utils/helper.py',
            'src/utils/format.py',
            'config/settings.json'
        ]
        tree_output = format_tree(files)
        self.assertIn('src', tree_output)
        self.assertIn('utils', tree_output)
        self.assertIn('config', tree_output)
        self.assertIn('├──', tree_output)  # Check for tree characters
        self.assertIn('└──', tree_output)

    def test_get_files_with_gitignore(self):
        """Test file collection respecting gitignore patterns"""
        # First, create the gitignore file
        with open('.gitignore', 'w') as f:
            f.write('*.log\n')
            f.write('temp/*\n')  # Changed from temp/ to temp/* to allow negation
            f.write('!temp/keep.txt\n')

        # Create test files that should be ignored
        os.makedirs('temp')
        with open('test.log', 'w') as f:
            f.write('log content')
        with open(os.path.join('temp', 'test.py'), 'w') as f:
            f.write('# test')
        with open(os.path.join('temp', 'keep.txt'), 'w') as f:
            f.write('keep this')

        config = {
            'include': ['.'],
            'exclude': [],
            'fileExtensions': ['.py', '.txt', '.log']
        }
        
        files = get_files('.', config)
        self.assertNotIn('test.log', files)
        self.assertNotIn('temp/test.py', files)
        self.assertIn('temp/keep.txt', files)  # Removed './' prefix

    def test_get_files_with_config_patterns(self):
        """Test file collection with config patterns"""
        # Create config files
        with open('package.json', 'w') as f:
            f.write('{}')
        with open('tsconfig.json', 'w') as f:
            f.write('{}')
        
        config = {
            'include': ['.'],
            'exclude': [],
            'fileExtensions': ['.json']
        }
        
        # Test without including configs
        files = get_files('.', config)
        self.assertNotIn('./package.json', files)
        self.assertNotIn('./tsconfig.json', files)
        
        # Test with including configs
        files = get_files('.', config, include_configs=True)
        self.assertIn('./package.json', files)
        self.assertIn('./tsconfig.json', files)

    def test_format_tree_empty(self):
        """Test tree formatting with empty input"""
        self.assertEqual(format_tree([]), '')

    def test_format_tree_nested(self):
        """Test tree formatting with deeply nested structure"""
        files = [
            'src/components/ui/button.js',
            'src/components/ui/input.js',
            'src/components/layout/header.js',
            'src/utils/format.js'
        ]
        tree = format_tree(files)
        self.assertIn('src', tree)
        self.assertIn('components', tree)
        self.assertIn('ui', tree)
        self.assertIn('layout', tree)
        self.assertIn('utils', tree)
        self.assertIn('button.js', tree)

    @patch('sys.argv')
    def test_main_with_all_options(self, mock_argv):
        """Test main function with various CLI options"""
        test_args = [
            'cpai',
            'src/',
            '-f', 'output.md',
            '--debug',
            '-a',
            '-c',
            '-x', 'tests/', 'docs/'
        ]
        mock_argv.__getitem__.side_effect = lambda i: test_args[i]
        mock_argv.__len__.return_value = len(test_args)

        with patch('cpai.main.cpai') as mock_cpai:
            main()
            mock_cpai.assert_called_once()
            cli_options = mock_cpai.call_args[0][1]
            self.assertEqual(cli_options['outputFile'], 'output.md')
            self.assertTrue(cli_options['include_all'])
            self.assertTrue(cli_options['include_configs'])
            self.assertEqual(cli_options['exclude'], ['tests/', 'docs/'])

    def test_write_output_large_content(self):
        """Test write_output with content exceeding chunk size"""
        config = {
            'outputFile': 'large_output.md',
            'usePastebin': True,
            'chunkSize': 10,  # Small chunk size for testing
            'files': ['src/main.py', 'src/utils.py']
        }
        content = "This is a test content"  # 22 characters (including spaces)
        
        with patch('builtins.print') as mock_print:
            write_output(content, config)
            mock_print.assert_any_call("\nWarning: Content size (22 characters) exceeds the maximum size (10 characters).")

    def test_get_files_with_custom_include(self):
        """Test file collection with custom include patterns"""
        os.makedirs(os.path.join(self.test_dir, 'custom'))
        with open(os.path.join(self.test_dir, 'custom', 'test.py'), 'w') as f:
            f.write('# test')

        config = {
            'include': ['custom/'],
            'exclude': [],
            'fileExtensions': ['.py']
        }
        
        files = get_files('.', config)
        self.assertIn('custom/test.py', files)
        self.assertNotIn('src/main.py', files)

    @patch('logging.warning')
    def test_cpai_no_files_found(self, mock_warning):
        """Test cpai function when no files are found"""
        cli_options = {
            'outputFile': False,
            'usePastebin': False,
            'include_all': False,
            'include_configs': False,
            'exclude': ['*']  # Exclude everything
        }
        
        cpai([], cli_options)
        mock_warning.assert_called_with("No files found to process")

    def test_read_config_with_invalid_fields(self):
        """Test reading config with various invalid fields"""
        config_data = {
            "include": "not_a_list",  # Should be a list
            "exclude": {"invalid": "type"},  # Should be a list
            "chunkSize": "not_an_int",  # Should be an integer
            "outputFile": []  # Should be bool or string
        }
        with open('cpai.config.json', 'w') as f:
            json.dump(config_data, f)
        
        config = read_config()
        self.assertEqual(config['include'], ['.'])  # Should use default
        self.assertEqual(config['exclude'], DEFAULT_EXCLUDE_PATTERNS)  # Should use default
        self.assertEqual(config['chunkSize'], DEFAULT_CHUNK_SIZE)  # Should use default
        self.assertFalse(config['outputFile'])  # Should use default

    def test_main_module_execution(self):
        """Test direct module execution through __main__.py"""
        with patch('sys.argv', ['cpai']):
            with patch('cpai.main.main') as mock_main:
                # Import and execute __main__.py directly
                import runpy
                runpy.run_module('cpai.__main__', run_name='__main__', alter_sys=True)
                mock_main.assert_called_once()

    def test_clipboard_error_handling(self):
        """Test clipboard operations with errors"""
        config = {
            'outputFile': False,
            'usePastebin': True,
            'chunkSize': 1000,
            'files': ['test.py']
        }
        content = "Test content"
        
        # Test subprocess error
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_popen.return_value = mock_process
            
            with patch('logging.error') as mock_error:
                write_output(content, config)
                mock_error.assert_called_with(
                    "Failed to copy to clipboard: Command returned non-zero exit status 1"
                )

        # Test encoding error
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = UnicodeEncodeError('utf-8', 'test', 0, 1, 'test error')
            with patch('logging.error') as mock_error:
                write_output(content, config)
                mock_error.assert_called_with(
                    "Failed to copy to clipboard: 'utf-8' codec can't encode character '\\x74' in position 0: test error"
                )

    def test_main_module_direct_execution(self):
        """Test direct execution through __main__.py"""
        with patch('sys.argv', ['cpai']):
            with patch('cpai.main.main') as mock_main:
                # Import and execute __main__.py
                import runpy
                runpy.run_module('cpai.__main__', run_name='__main__')
                mock_main.assert_called_once()

    def test_format_tree_with_empty_subtree(self):
        """Test tree formatting with empty subtree"""
        files = [
            'src/empty/',
            'src/file.py'
        ]
        tree = format_tree(files)
        self.assertIn('src', tree)
        self.assertIn('empty', tree)
        self.assertIn('file.py', tree)

    def test_get_files_with_broken_symlinks(self):
        """Test file collection with broken symlinks"""
        # Create a broken symlink
        os.symlink('nonexistent.py', 'broken_link.py')
        
        config = {
            'include': ['.'],
            'exclude': [],
            'fileExtensions': ['.py']
        }
        
        try:
            files = get_files('.', config)
            self.assertNotIn('broken_link.py', files)
        finally:
            os.unlink('broken_link.py')

    def test_write_output_with_unicode_error(self):
        """Test clipboard operations with Unicode errors"""
        config = {
            'outputFile': False,
            'usePastebin': True,
            'chunkSize': 1000,
            'files': ['test.py']
        }

        # Create content with problematic Unicode
        content = "Test content with unicode \udcff"

        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.side_effect = UnicodeEncodeError(
                'utf-8', content, 26, 27, 'surrogates not allowed'
            )
            mock_popen.return_value = mock_process

            with patch('logging.error') as mock_error:
                write_output(content, config)
                mock_error.assert_called_with(
                    "Failed to copy to clipboard: 'utf-8' codec can't encode character '\\udcff' in position 26: surrogates not allowed"
                )

    def test_format_tree_with_special_characters(self):
        """Test tree formatting with special characters in paths"""
        files = [
            'src/special!@#$/file.py',
            'src/unicode⚡/test.py'
        ]
        tree = format_tree(files)
        self.assertIn('special!@#$', tree)
        self.assertIn('unicode⚡', tree)

    def test_main_with_keyboard_interrupt(self):
        """Test main function handling KeyboardInterrupt"""
        mock_args = MagicMock()
        mock_args.debug = False
        mock_args.file = None
        mock_args.noclipboard = False
        mock_args.all = False
        mock_args.configs = False
        mock_args.exclude = None
        mock_args.files = []

        with patch('argparse.ArgumentParser.parse_args', return_value=mock_args):
            with patch('cpai.main.cpai', side_effect=KeyboardInterrupt):
                with patch('sys.exit') as mock_exit:
                    with patch('logging.error') as mock_error:
                        main()
                        mock_exit.assert_called_once_with(1)
                        mock_error.assert_called_once()

    def test_get_files_with_permission_error(self):
        """Test file collection with permission errors"""
        # Create a directory with no read permissions
        os.makedirs('no_access')
        os.chmod('no_access', 0o000)
        
        config = {
            'include': ['.'],
            'exclude': [],
            'fileExtensions': ['.py']
        }
        
        try:
            files = get_files('.', config)
            self.assertNotIn('no_access/test.py', files)
        finally:
            os.rmdir('no_access')

    def test_write_output_clipboard_errors(self):
        """Test clipboard operations with various errors"""
        config = {
            'outputFile': False,
            'usePastebin': True,
            'chunkSize': 1000,
            'files': ['test.py']
        }
        content = "Test content"

        # Test non-zero return code
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_popen.return_value = mock_process
            
            with patch('logging.error') as mock_error:
                write_output(content, config)
                mock_error.assert_called_with(
                    "Failed to copy to clipboard: Command returned non-zero exit status 1"
                )

        # Test subprocess error
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = subprocess.CalledProcessError(1, 'pbcopy')
            with patch('logging.error') as mock_error:
                write_output(content, config)
                mock_error.assert_called_with(
                    "Failed to copy to clipboard: Command 'pbcopy' returned non-zero exit status 1"
                )

        # Test encoding error
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = UnicodeEncodeError('utf-8', 'test', 0, 1, 'test error')
            with patch('logging.error') as mock_error:
                write_output(content, config)
                mock_error.assert_called_with(
                    "Failed to copy to clipboard: 'utf-8' codec can't encode character '\\x74' in position 0: test error"
                )

if __name__ == '__main__':
    unittest.main()
