"""Constants used throughout cpai."""

DEFAULT_CHUNK_SIZE = 90000

# Default patterns to exclude from processing
DEFAULT_EXCLUDE_PATTERNS = [
    # Build and cache
    "**/build/**", "**/dist/**", "**/__pycache__/**", "**/.cache/**",
    "**/coverage/**", "**/.next/**", "**/out/**", "**/.nuxt/**",
    "**/.output/**", "**/*.egg-info/**",
    
    # Dependencies
    "**/node_modules/**", "**/venv/**", "**/virtualenv/**",
    "**/env/**", "**/.env/**", "**/.venv/**",
    
    # Test files
    "**/test/**", "**/tests/**", "**/__tests__/**",
    "**/*.test.*", "**/*.spec.*",
    
    # IDE and OS
    "**/.idea/**", "**/.vscode/**", "**/.DS_Store",
    
    # Version Control
    "**/.git/**", "**/.svn/**", "**/.hg/**",
    
    # Logs and temp files
    "**/*.log", "**/npm-debug.log*", "**/yarn-debug.log*", "**/yarn-error.log*",
    
    # Dotfiles and dotfolders
    "**/.env", "**/.envrc", "**/.env.*",
    "**/.python-version", "**/.ruby-version", "**/.node-version",
    
    # Config files
    "**/package.json", "**/package-lock.json", "**/yarn.lock",
    "**/tsconfig.json", "**/jsconfig.json", "**/*.config.js",
    "**/pyproject.toml", "**/setup.py", "**/setup.cfg",
    "**/requirements.txt", "**/Pipfile", "**/Pipfile.lock",
    "**/bower.json", "**/composer.json", "**/composer.lock",
    
    # Build outputs
    "**/*.min.js", "**/*.min.css", "**/*.map",
    "**/dist/**", "**/build/**", "**/target/**",
    
    # Binary and media files
    "**/*.jpg", "**/*.jpeg", "**/*.png", "**/*.gif", "**/*.ico",
    "**/*.pdf", "**/*.zip", "**/*.tar.gz", "**/*.tgz",
    "**/*.woff", "**/*.woff2", "**/*.ttf", "**/*.eot",
    "**/*.mp3", "**/*.mp4", "**/*.mov", "**/*.avi"
]

# Core source file patterns by directory
CORE_SOURCE_PATTERNS = {
    # JavaScript/TypeScript/React
    "src/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "app/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "pages/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "components/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "lib/": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    
    # Python
    "src/": ["*.py"],
    "app/": ["*.py"],
    "lib/": ["*.py"]
}

# Default supported file extensions
DEFAULT_FILE_EXTENSIONS = [
    ".ts", ".js", ".py", ".rs", ".sol", ".go", ".jsx", ".tsx",
    ".css", ".scss", ".svelte", ".html", ".java", ".c", ".cpp",
    ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
    ".bash", ".md", ".json", ".yaml", ".yml", ".toml"
]
