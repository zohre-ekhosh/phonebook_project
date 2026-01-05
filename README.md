# Phonebook Management System

A phonebook application with contact management, advanced search, and user role support.

## Features
- Persian RTL (Right-to-Left) user interface
- Two user roles (Normal User & Admin)
- Advanced search across 6 different fields
- Add, edit and delete in Admin mode
- Profile photo support
- Import contacts from CSV files
- Iranian phone number validation
- SQLite database

## Installation Methods

### Method 1: Pure Version (Without Docker)
```bash
# 1. Install Python and pip
# 2. Clone the project
git clone https://github.com/zohre-ekhosh/phonebook_project.git
cd phonebook_project

# 3. Install requirements
pip install -r requirements.txt

# 4. Run the application
python main.py