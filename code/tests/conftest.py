import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
code_dir = repo_root / "code"

if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
