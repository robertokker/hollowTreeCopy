# Hollow Tree Generator

## Overview
The **Hollow Tree Generator** is a Python utility designed to replicate large directory structures (up to 2TB) for testing or archival purposes. It creates empty (0-byte) "dummy" files for most content, while allowing you to selectively perform a "full copy" of specific files based on powerful Regular Expression (Regex) rules.

## Features
- **Hollow Copy**: Replicates exact folder structures with lightweight dummy files.
- **Smart Rules**: Use Regex to define exactly which files to fully copy (e.g., `.*\.json$`) and which to exclude completely.
- **Regex Helper**: Built-in cheat sheet and link to regexr.com to help you write patterns.
- **Two-Step Workflow**: 
  1. **Scan**: Analyze the source and see a detailed report (File counts, estimated size).
  2. **Copy**: Execute the operation with a precise progress bar.
- **Settings Persistence**: Your rules are automatically saved to `hollow_tree_settings.json`.
- **Modern UI**: Clean dark theme for comfortable usage.

## Safety & Security 🛡️
This tools allows for legal copying of huge datasets, so safety is paramount:
1. **Recursion Guard**: You cannot set the Export folder *inside* the Input folder. This prevents infinite loops where the script tries to copy the files it is currently generating.
2. **Identity Guard**: You cannot select the same folder for Input and Export.
3. **Overwrite Protection**: If the Export folder is not empty, the system warns you explicitly before any action is taken.
4. **Read-Only Source**: The script never modifies your Input folder.

## Usage

### Prerequisites
- Python 3.x (with Tkinter installed, which is standard).

### Running the App
```bash
python hollow_tree.py
```

### Workflow
1. **Select Paths**:
   - **Input Folder**: The source directory you want to copy.
   - **Export Path**: Where the new structure will be created.
2. **Configure Rules (Settings Tab)**:
   - **Full Copy Rules**: Files matching these Regex patterns will be copied fully.
     - Example: `.*\.json$` (All JSON files)
     - Example: `^metadata` (Files starting with 'metadata')
   - **Exclude Rules**: Files matching these will be ignored completely.
     - Example: `.*\.tmp$` (Temporary files)
3. **Scan**:
   - Click **1. Scan**.
   - Review the **Activity Log** at the bottom to see how many files will be hollowed vs locally copied.
4. **Copy**:
   - Click **2. Copy Files**.
   - Monitor the progress bar until completion.
