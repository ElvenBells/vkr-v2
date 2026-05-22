"""
CV-AI Test Automation Framework
Core package initialization.
"""
__version__ = "0.1.0"
__author__ = "AI QA Research Lab"

import sys
import pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))