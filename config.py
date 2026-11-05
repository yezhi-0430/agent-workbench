from pathlib import Path
import os

def load_env(path=None):
    path = Path(path) if path else Path(__file__).resolve().parent / '.env'
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if key in ('OPENROUTER_API_KEY', 'OPENROUTER_MODEL') and value:
            os.environ.setdefault(key, value)
