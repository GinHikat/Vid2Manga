import pandas as pd
import numpy as np
import io
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
import tempfile
import subprocess
import os, sys
import json
import time

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

#File format changes
def save_to_txt(text: str, file_name: str):
    with open(f"D:/Study/Education/Projects/Group_Project/source/document/text_format/{file_name}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("File saved as output.txt")

def print_tree(folder_path, prefix=""):
    '''
    Print the folder files and subfolders in hierarchy tree format

    Input:
        folder_path: path to folder
    
    Output:
        print the tree structure
    '''

    try:
        items = sorted(os.listdir(folder_path))
    except PermissionError:
        print(prefix + "└── [Permission Denied]")
        return

    for i, item in enumerate(items):
        path = os.path.join(folder_path, item)
        connector = "└── " if i == len(items) - 1 else "├── "

        print(prefix + connector + item)

        if os.path.isdir(path):
            extension = "    " if i == len(items) - 1 else "│   "
            print_tree(path, prefix + extension)
