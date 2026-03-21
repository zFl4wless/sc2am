# Contributing to SC2AM

Thank you for your interest in contributing to SC2AM! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and considerate of others.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Provide a clear title and description
3. Include:
   - macOS version
   - Python version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs

### Suggesting Features

1. Describe the feature and use case
2. Explain why it would be valuable
3. Provide examples of how it would be used

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make changes** following the code style
5. **Update documentation** as needed
6. **Commit with clear messages**: `git commit -m "Add feature: description"`
7. **Push to your fork**: `git push origin feature/my-feature`
8. **Open a Pull Request** with detailed description

## Development Setup

```bash
# Clone your fork
git clone https://github.com/zfl4wless/sc2am.git
cd sc2am

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
# pip install -r requirements-dev.txt  # When available
```

## Code Style

- **Python**: Follow PEP 8
- **Naming**: Clear, descriptive names
- **Documentation**: Docstrings for all functions/classes
- **Comments**: Explain "why", not "what"

### Example function:
```python
def download(self, url: str) -> Tuple[bool, Optional[Path], str]:
    """
    Download audio from URL.
    
    Args:
        url: URL to download from
        
    Returns:
        Tuple of (success, file_path, message)
    """
    # Implementation
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to code
- Include examples for new features

## Commit Message Guidelines

- Use clear, descriptive titles
- Reference issues: `Fix #123`
- Start with imperative: "Add feature", not "Added feature"

Examples:
- `Fix: Handle empty URLs in batch file`
- `Add: Support for Spotify playlists`
- `Docs: Update installation instructions`
- `Refactor: Simplify downloader logic`

## Pull Request Process

1. Update documentation
2. Keep commits clean and organized
3. Provide clear description of changes

## Areas for Contribution

- Bug fixes
- Documentation improvements
- New features (discuss first via issue)
- Performance improvements
- Code quality/refactoring
- Platform support (Windows, Linux)

## Questions?

Feel free to open an issue for any questions about contributing.

---

Thank you for helping improve SC2AM!
