import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pygame
except ImportError:
    print("pygame is not installed. In the VS Code terminal run:\n\n    pip install -r requirements.txt\n")
    sys.exit(1)

from petbalance.app import main

if __name__ == "__main__":
    main()
