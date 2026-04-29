import os
import sys

_BASE = os.path.dirname(os.path.abspath(__file__))
for _sub in ("core", "ui", "modes", "screens"):
    _path = os.path.join(_BASE, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from game import *

if __name__ == "__main__":
    main()
