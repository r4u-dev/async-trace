# Publishing to PyPI

This guide walks you through publishing `async-trace` to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on:
   - [Test PyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

2. **API Tokens**: Generate API tokens for both accounts:
   - Test PyPI: https://test.pypi.org/manage/account/token/
   - PyPI: https://pypi.org/manage/account/token/

3. **Install Build Tools**:
   ```bash
   pip install --upgrade build twine
   ```

## Before Publishing

### 1. Update Version

Edit `pyproject.toml` and update the version number:
```toml
[project]
version = "0.1.1"  # Increment appropriately
```

Also update the version in `async_trace/__init__.py`:
```python
__version__ = "0.1.1"
```

### 2. Update CHANGELOG

Add the changes to `README.md` under the Changelog section.

### 3. Update Metadata

In `pyproject.toml`, update:
- `authors` - Add your name and email
- `urls` - Update GitHub username/repository

### 4. Test Locally

```bash
# Install in editable mode
pip install -e .

# Run the examples
python examples/basic_example.py
python examples/structured_trace.py
python examples/parallel_tasks.py
```

### 5. Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

## Building the Package

Build the distribution files:

```bash
python -m build
```

This creates:
- `dist/async_trace-0.1.0-py3-none-any.whl` (wheel)
- `dist/async-trace-0.1.0.tar.gz` (source distribution)

## Publishing to Test PyPI (Recommended First)

Test your package on Test PyPI before publishing to the real PyPI:

```bash
python -m twine upload --repository testpypi dist/*
```

When prompted, use:
- Username: `__token__`
- Password: Your Test PyPI API token (starting with `pypi-`)

### Test Installation from Test PyPI

```bash
# Create a test environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ async-trace

# Test it works
python -c "from async_trace import print_trace; print('Success!')"

# Clean up
deactivate
rm -rf test_env
```

## Publishing to PyPI (Production)

Once you've verified everything works on Test PyPI:

```bash
python -m twine upload dist/*
```

When prompted, use:
- Username: `__token__`
- Password: Your PyPI API token (starting with `pypi-`)

### Verify Publication

1. Check the package page: https://pypi.org/project/async-trace/
2. Install from PyPI:
   ```bash
   pip install async-trace
   ```
3. Test the installation:
   ```bash
   python -c "from async_trace import print_trace; print('Success!')"
   ```

## Using GitHub Actions (Optional)

For automated publishing, you can set up GitHub Actions. Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Then add your PyPI API token as a GitHub secret named `PYPI_API_TOKEN`.

## Troubleshooting

### Version Already Exists

PyPI doesn't allow re-uploading the same version. You must:
1. Increment the version number
2. Rebuild the package
3. Upload again

### Authentication Failed

- Make sure you're using `__token__` as the username (exactly as shown)
- Verify your API token is correct and hasn't expired
- Check that the token has the right permissions

### Package Name Already Taken

If `async-trace` is taken, you'll need to:
1. Choose a different name
2. Update `pyproject.toml` and all documentation
3. Try publishing again

## Release Checklist

- [ ] Version incremented in `pyproject.toml`
- [ ] Version incremented in `async_trace/__init__.py`
- [ ] CHANGELOG updated in README.md
- [ ] All tests passing locally
- [ ] Examples run successfully
- [ ] Clean build directory (`rm -rf dist/ build/`)
- [ ] Package built (`python -m build`)
- [ ] Tested on Test PyPI
- [ ] Published to PyPI
- [ ] Installation verified from PyPI
- [ ] Git tag created (`git tag v0.1.0 && git push --tags`)
- [ ] GitHub release created

## Useful Commands

```bash
# Check package metadata
python -m twine check dist/*

# View package contents
tar -tzf dist/async-trace-*.tar.gz

# Install specific version
pip install async-trace==0.1.0

# Uninstall
pip uninstall async-trace
```

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)

