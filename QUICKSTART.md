# Quick Start Guide

## Project Structure

Your project is now structured as a proper Python package ready for PyPI:

```
async-trace/
├── async_trace/              # Main package
│   ├── __init__.py          # Public API exports
│   └── tracer.py            # Core tracing functionality
├── examples/                 # Usage examples
│   ├── basic_example.py
│   ├── parallel_tasks.py
│   └── structured_trace.py
├── dist/                     # Build artifacts (gitignored)
│   ├── async_trace-0.1.0-py3-none-any.whl
│   └── async_trace-0.1.0.tar.gz
├── pyproject.toml           # Package metadata & build config
├── README.md                # Main documentation
├── LICENSE                  # MIT License
├── MANIFEST.in              # Additional files to include
├── PUBLISHING.md            # PyPI publishing guide
└── .gitignore              # Git ignore patterns
```

## Before Publishing to PyPI

You need to update a few placeholders in `pyproject.toml`:

### 1. Update Author Information

Edit `pyproject.toml`:
```toml
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
```

Replace with your actual name and email.

### 2. Update Repository URLs

Edit `pyproject.toml`:
```toml
[project.urls]
Homepage = "https://github.com/yourusername/async-trace"
Repository = "https://github.com/yourusername/async-trace"
Documentation = "https://github.com/yourusername/async-trace#readme"
"Bug Tracker" = "https://github.com/yourusername/async-trace/issues"
```

Replace `yourusername` with your actual GitHub username, or update to your repository URL.

## Local Development

### Install in Editable Mode

```bash
pip install -e .
```

This allows you to make changes to the code and test them immediately.

### Run Examples

```bash
python examples/basic_example.py
python examples/structured_trace.py
python examples/parallel_tasks.py
```

### Run Your Own Code

```python
import asyncio
from async_trace import print_trace

async def my_task():
    print_trace()
    
asyncio.run(my_task())
```

## Building the Package

```bash
# Install build tool
pip install --upgrade build

# Build the package
python -m build
```

This creates wheel and source distributions in `dist/`.

## Publishing to PyPI

Follow the detailed guide in `PUBLISHING.md`:

1. **Test on Test PyPI first** (recommended)
2. **Publish to PyPI** when ready

Quick commands:
```bash
# Install twine
pip install --upgrade twine

# Publish to Test PyPI
python -m twine upload --repository testpypi dist/*

# Publish to PyPI (production)
python -m twine upload dist/*
```

## Git Setup

### Initialize Git (if not done)

```bash
git init
git add .
git commit -m "Initial commit: restructured for PyPI"
```

### Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `async-trace`
3. Push your code:

```bash
git remote add origin https://github.com/yourusername/async-trace.git
git branch -M main
git push -u origin main
```

### Create Releases

After publishing to PyPI, create a GitHub release:

```bash
git tag v0.1.0
git push --tags
```

Then create a release on GitHub from the tag.

## Testing the Published Package

After publishing to PyPI, anyone can install it:

```bash
pip install async-trace
```

Test the installation:

```python
python -c "from async_trace import print_trace; print('Success!')"
```

## Next Steps

1. ✅ Update author info in `pyproject.toml`
2. ✅ Update repository URLs in `pyproject.toml`
3. ✅ Create GitHub repository
4. ✅ Push code to GitHub
5. ✅ Test build: `python -m build`
6. ✅ Publish to Test PyPI (optional but recommended)
7. ✅ Publish to PyPI: `python -m twine upload dist/*`
8. ✅ Create GitHub release with tag
9. ✅ Share with the community!

## Common Commands

```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Rebuild package
python -m build

# Check package metadata
python -m twine check dist/*

# Install locally for testing
pip install -e .

# Uninstall
pip uninstall async-trace

# Install from PyPI (after publishing)
pip install async-trace
```

## Need Help?

- See `PUBLISHING.md` for detailed publishing instructions
- See `README.md` for API documentation and usage examples
- Check out the `examples/` directory for working code samples

Happy publishing! 🚀

