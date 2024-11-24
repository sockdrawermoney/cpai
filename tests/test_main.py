import os
import tempfile
import shutil
import unittest
from pathlib import Path
from cpai.main import get_files
from cpai.constants import DEFAULT_EXCLUDE_PATTERNS

class TestGetFiles(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create some test files and directories
        self.create_test_files()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def create_test_files(self):
        """Create a test directory structure."""
        # Create Python files
        Path(self.test_dir, "main.py").write_text("def main(): pass")
        Path(self.test_dir, "__init__.py").write_text("")
        Path(self.test_dir, "constants.py").write_text("VERSION = '1.0.0'")
        
        # Create a subdirectory with files
        subdir = Path(self.test_dir, "subdir")
        subdir.mkdir()
        Path(subdir, "module.py").write_text("def func(): pass")
        
        # Create files that should be excluded
        pycache_dir = Path(self.test_dir, "__pycache__")
        pycache_dir.mkdir()
        Path(pycache_dir, "main.cpython-39.pyc").write_text("")
        
        # Create test files (should be excluded by default)
        test_dir = Path(self.test_dir, "tests")
        test_dir.mkdir()
        Path(test_dir, "test_main.py").write_text("def test_main(): pass")
        
        # Create config files
        Path(self.test_dir, "setup.py").write_text("from setuptools import setup")
        Path(self.test_dir, "requirements.txt").write_text("pathspec==0.11.0")

    def test_get_files_basic(self):
        """Test basic file filtering with default configuration."""
        config = {
            'include': ['.'],
            'fileExtensions': ['.py']  # Only process Python files
        }
        files = get_files(self.test_dir, config)

        # Convert absolute paths to relative for comparison
        rel_files = [os.path.relpath(f, self.test_dir) for f in files]

        # Should include Python files in root and subdirectories
        expected = {
            "main.py",
            "__init__.py",
            "constants.py",
            os.path.join("subdir", "module.py")
        }
        self.assertEqual(set(rel_files), expected)

    def test_get_files_with_absolute_path(self):
        """Test that get_files works correctly with absolute paths."""
        abs_path = os.path.abspath(self.test_dir)
        files = get_files(abs_path)

        # All returned paths should be absolute
        self.assertTrue(all(os.path.isabs(f) for f in files))

    def test_get_files_with_relative_path(self):
        """Test that get_files works correctly with relative paths."""
        # Get current directory
        current_dir = os.getcwd()
        try:
            # Change to parent of test directory
            os.chdir(os.path.dirname(self.test_dir))
            # Use relative path
            rel_path = os.path.basename(self.test_dir)
            files = get_files(rel_path)

            # All returned paths should be absolute
            self.assertTrue(all(os.path.isabs(f) for f in files))
            self.assertTrue(all(os.path.exists(f) for f in files))
        finally:
            # Restore current directory
            os.chdir(current_dir)

    def test_get_files_exclude_patterns(self):
        """Test that exclude patterns work correctly."""
        # Create a custom exclude pattern
        config = {
            'exclude': ['**/subdir/**']  # Exclude the subdir directory
        }
        
        files = get_files(self.test_dir, config=config)
        rel_files = [os.path.relpath(f, self.test_dir) for f in files]
        
        # Should not include files from subdir
        self.assertFalse(any("subdir" in f for f in rel_files))

    def test_get_files_include_patterns(self):
        """Test that include patterns work correctly."""
        # Create a custom include pattern
        config = {
            'include': ['**/subdir/**'],  # Only include files in subdir
            'fileExtensions': ['.py']  # Only process Python files
        }
        
        files = get_files(self.test_dir, config=config)
        rel_files = [os.path.relpath(f, self.test_dir) for f in files]
        
        # Should only include files from subdir
        self.assertTrue(all("subdir" in f for f in rel_files))

    def test_get_files_symlinks(self):
        """Test that symlinks are handled correctly."""
        config = {
            'include': ['.'],
            'fileExtensions': ['.py']  # Only process Python files
        }
        
        # Create a symlink to a Python file
        source = Path(self.test_dir, "main.py")
        link = Path(self.test_dir, "main_link.py")
        os.symlink(source, link)
        
        try:
            files = get_files(self.test_dir, config)
            rel_files = [os.path.relpath(f, self.test_dir) for f in files]
            
            # Should include both the original file and the symlink
            self.assertTrue(any("main.py" in f for f in rel_files))
            self.assertTrue(any("main_link.py" in f for f in rel_files))
        finally:
            # Cleanup
            if os.path.exists(link):
                os.remove(link)

    def test_get_files_broken_symlinks(self):
        """Test that broken symlinks are handled gracefully."""
        # Create a broken symlink
        nonexistent = Path(self.test_dir, "nonexistent.py")
        link = Path(self.test_dir, "broken_link.py")
        os.symlink(nonexistent, link)
        
        # Should not raise an exception
        files = get_files(self.test_dir)
        rel_files = [os.path.relpath(f, self.test_dir) for f in files]
        
        # Should not include the broken symlink
        self.assertFalse("broken_link.py" in rel_files)

if __name__ == '__main__':
    unittest.main()
