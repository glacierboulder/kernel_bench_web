from pathlib import Path
import hashlib
import json
import shutil
import tempfile

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'source-bundle-parts.json').read_text(encoding='utf-8'))
for name, record in manifest.items():
    target = root / name
    if target.is_file() and hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() == record['sha256']:
        print('Verified', name)
        continue
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        for part in record['parts']:
            with (root / part).open('rb') as source:
                shutil.copyfileobj(source, tmp)
    with temporary.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != record['sha256']:
        temporary.unlink()
        raise SystemExit(f'SHA-256 mismatch: {name}')
    temporary.replace(target)
    print('Restored and verified', name)
