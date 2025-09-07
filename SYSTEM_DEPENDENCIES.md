# System Dependencies

This project requires certain system-level libraries to be installed before running.

## Required System Libraries

### libmagic (File Type Detection)
Required for MIME type detection in file imports.

**macOS (Homebrew):**
```bash
brew install libmagic
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libmagic1
```

**CentOS/RHEL/Fedora:**
```bash
sudo yum install file-libs
# or on newer versions:
sudo dnf install file-libs
```

**Windows:**
```bash
# Using chocolatey
choco install file

# Or download from: https://github.com/julian-r/python-magic#windows
```

## Verification

Test that the system dependencies are properly installed:

```bash
python -c "import magic; print('libmagic is working!')"
```

## Docker

If using Docker, these dependencies are handled automatically in the Dockerfile.