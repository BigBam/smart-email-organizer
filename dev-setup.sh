#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Smart Email Organizer...${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment
echo -e "${BLUE}Creating virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install required packages
echo -e "${BLUE}Installing required packages...${NC}"
pip install openai google-api-python-client google-auth-httplib2 google-auth-oauthlib

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${BLUE}To activate the virtual environment in the future, run:${NC}"
echo "source venv/bin/activate"
echo -e "${BLUE}To run the scripts:${NC}"
echo "python3 gmail_old_labeler.py"
echo "python3 gmail_ai_labeler.py" 