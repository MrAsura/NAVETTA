"""
Run all tests given as a parameter
"""

import pkgutil as pkgu
import sys
import os
import runpy

test_scripts = {} #Dict of all test scripts in the tests package and the respective entry points 

__path = [os.path.abspath(r"tests"),]
if "__path__" in globals():
    __path = __path__
for loader, module_name, is_pkg in pkgu.walk_packages(__path):
    if not is_pkg and "__main__" != module_name:
        module = loader.find_module(module_name).load_module(module_name)
        test_scripts[module_name] = getattr(module, "main", lambda: runpy.run_module(module))
        

def main():
    # Get (a list of) test scripts to run
    if len(sys.argv) > 1:
        scripts = sys.argv[1:]
    else:
        scripts = map(str.strip, input("Give test scripts to run as a comma separated list: ").split(sep = ','))

    # Process tests
    num_scripts_run = 0
    for script in scripts:
        test_func = None
        if script in test_scripts:
            # Given script is in test_scripts
            test_func = test_scripts[script]()
        elif ".py" in script:
            # Possiply a external script given run it directly
            test_func = lambda: runpy.run_path(script)
        else:
            print("Script {} not found.".format(script))

        if test_func:
            print("Running test {}".format(script))
            test_func()
            num_scripts_run += 1

    if num_scripts_run == 0:
        print("No valid script given.")


if __name__ == "__main__":
    main()