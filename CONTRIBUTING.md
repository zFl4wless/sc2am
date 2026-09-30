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

1. **Fork the repository** (or create a branch if you have repository access)
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make changes** following the code style
4. **Update documentation** as needed
5. **Run the focused tests and checks** described below
6. **Commit with a conventional message**, for example:
   `git commit -m "docs: adds setup guidance"`
7. **Push to your fork**: `git push origin feature/my-feature`
8. **Open a Pull Request** with a detailed description

## Development Setup

```bash
# Clone your fork
git clone https://github.com/zfl4wless/sc2am.git
cd sc2am

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt
```

The repository supports Python 3.10 and newer. The commands below assume the
virtual environment is active.

Dependency policy:
- `pyproject.toml` is the single source of truth for runtime and development dependencies.
- `requirements.txt` and `requirements-dev.txt` are compatibility wrappers for tooling and local workflows.

## Code Style

- **Python**: Follow PEP 8, format with Black
- **Naming**: Clear, descriptive names
- **Documentation**: Add docstrings for modules/classes and non-trivial functions
- **Comments**: Explain "why", not "what"

## Verification

Run the full test suite and the same formatting/lint checks used by CI before
opening a pull request:

```bash
PYTHONPATH=. pytest -q
black --check .
flake8 sc2am tests
```

When changing CLI behavior, also run `sc2am --help` and the relevant command
with `--dry-run` so no files or Music.app actions are triggered during a
manual check.

### Example function:
```python
def download(self, url: str):
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

### Repository Guides

- `AGENTS.md` for agent-friendly working rules and project-specific context
- `docs/commands.md` for setup, test, lint, and release commands
- `docs/releasing.md` for the release checklist
- `CHANGELOG.md` for user-facing release history and entry format
- `docs/architecture.md` for module responsibilities and data flow
- `.github/pull_request_template.md` for a consistent PR format

## Commit Message Guidelines

- Use clear, descriptive titles with conventional prefixes seen in this repo, such as `fix:`, `feat:`, `chore:`, `docs:`, `refactor:`
- Keep the prefix and summary in lower-case style (for example `feat: adds ...`)
- Reference issues where relevant, for example `fix: adds retry for timeout handling (#123)`

Examples:
- `fix: adds handling for empty URLs in batch files`
- `feat: adds support for Spotify playlists`
- `docs: adds installation troubleshooting notes`
- `refactor: adds clearer downloader flow boundaries`

## Pull Request Process

1. Update documentation
2. Keep commits clean and organized
3. Run the verification commands above
4. Provide a clear description using `.github/pull_request_template.md`
5. Link the related issue and explain any behavior or compatibility impact

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
