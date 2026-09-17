"""Cross-language bundle pins: SHA256 of sorted relative path NUL file digest LF."""
import hashlib
from pathlib import Path
from .contract import require

def bundle_digest(root, kind):
    root=Path(root).resolve()
    if kind=='pilot':
        paths=[root/'package.json', *sorted((root/'src').rglob('*.js')), *sorted((root/'bin').rglob('*.js'))]
    elif kind=='momo':
        paths=[p for p in root.rglob('*') if p.is_file() and p.suffix in {'.md','.py','.sh'} and '__pycache__' not in p.parts]
    else: raise ValueError('unknown bundle kind')
    require(paths and all(p.is_file() for p in paths),'bundle incomplete')
    manifest=''.join(f'{p.relative_to(root).as_posix()}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\n' for p in sorted(set(paths)))
    return hashlib.sha256(manifest.encode()).hexdigest()
