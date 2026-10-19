import sys
import os

# Ensure project root is on sys.path so `modules.*` imports resolve under pytest
sys.path.insert(0, os.path.dirname(__file__))