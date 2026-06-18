import os
import sys

# tests/ 의 부모(repo 루트) 아래 scripts/ 를 import 경로에 추가한다.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
