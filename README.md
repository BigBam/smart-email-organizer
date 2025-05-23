# Smart Email Organizer

A GUI application that helps you organize your Gmail inbox by automatically applying labels based on custom rules you create. The application provides an intuitive interface to:

1. Create and manage custom rules for email labeling
2. Manage Gmail labels
3. Process emails in bulk with your rules
4. Monitor account statistics

## Prerequisites

- Python 3.x
- Gmail account
- Google Cloud Project with Gmail API enabled

## Setup Instructions

1. **Create and activate a virtual environment**

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

2. **Install required packages**

```bash
pip install -r requirements.txt
```

3. **Set up Google Cloud Project and Gmail API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `credentials.json` in the project directory

## Usage

1. Make sure your virtual environment is activated
2. Run the application:

```bash
python gmail_labeler_gui.py
```

On first run, you'll need to authenticate with your Google account through a browser window.

## Features

### Rules Management
- Create custom rules based on email subject, sender, or recipient
- Define conditions like "contains", "equals", "starts with", or "ends with"
- Apply labels or move emails to specific categories
- Save and manage multiple rules

### Label Management
- View all existing Gmail labels
- Create new custom labels
- Delete existing labels (except system labels)

### Email Processing
- Process emails in bulk with your rules
- Pause/resume processing
- Real-time progress monitoring
- Detailed logging of operations

### Account Information
- View account statistics
- Monitor total messages and threads
- Logout functionality

## Files

- `gmail_labeler_gui.py`: Main GUI application
- `gmail_apply_rules.py`: Core functionality for applying rules to emails
- `credentials.json`: Your Google Cloud credentials (not included in repo)
- `token.json`: Generated after first authentication (not included in repo)
- `rules.json`: Stores your custom rules (not included in repo)

## Security Notes

- Never commit `credentials.json` or `token.json` to version control
- Add these files to your `.gitignore`:

```
credentials.json
token.json
__pycache__/
*.pyc
venv/
```

## Development

### Development Setup

The project includes a `dev-setup.sh` script that automates the initial development environment setup:

```bash
# Run the setup script
./dev-setup.sh
```

This script will:
1. Check for Python 3 installation
2. Create and activate a virtual environment
3. Upgrade pip to the latest version
4. Install all required dependencies

### Build Scripts

The project includes platform-specific build scripts to create standalone executables:

#### Windows Build (`build_windows.py`)
This script creates a Windows executable using PyInstaller:
- Installs required build dependencies
- Generates a PyInstaller spec file
- Creates a standalone executable in the `dist` directory
- Includes a README.txt with first-run instructions
- Handles icon packaging

To build for Windows:
```bash
python build_windows.py
```

#### macOS Build (`build_macos.py`)
This script creates a macOS application bundle:
- Generates application icons using `create_icons.py`
- Copies platform-specific icons
- Builds the application using PyInstaller
- Creates a `.app` bundle in the `dist` directory
- Supports DMG creation using `create-dmg`

To build for macOS:
```bash
python build_macos.py
```

### Project Structure
- `setup.py`: Defines the Python package configuration
- `build_windows.py`: Script for building Windows executable
- `build_macos.py`: Script for building macOS application
- `create_icons.py`: Script for generating application icons
- `dev-setup.sh`: Development environment setup script

### Dependencies
The project uses the following main dependencies:
- wxPython: For the GUI
- Google API Client: For Gmail API integration
- Python-dateutil: For date handling
- PyInstaller: For building executables

All dependencies are listed in `requirements.txt` and can be installed using pip.

### Building the Application

#### Windows
To build the Windows executable:
```bash
python build_windows.py
```
The executable will be created in the `dist` directory.

#### macOS
To build the macOS application:
```bash
# First install create-dmg if you haven't already
brew install create-dmg

# Build the application
python build_macos.py

# Create the DMG installer
create-dmg "Gmail Labeler" dist/Gmail\ Labeler.app
```