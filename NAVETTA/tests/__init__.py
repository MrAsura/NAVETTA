"""
Only include test script files in * import
"""

from .__main__ import test_scripts, main

__all__ = test_scripts.keys()