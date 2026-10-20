"""Materialize a text source patch against the supervisor's immutable baseline."""
import difflib
import os
from pathlib import Path
import stat


def source_files(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('source root must be a real directory')
    result = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
        for name in dirs + files:
            path = Path(parent) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise ValueError('submission contains symlink or special file')
        for name in files:
            path = Path(parent) / name
            relative = path.relative_to(root).as_posix()
            if any(c in relative for c in '\n\r\t"\\'):
                raise ValueError('unsupported source filename')
            result[relative] = path
    return result


def materialize(baseline, modified, destination):
    before, after = source_files(baseline), source_files(modified)
    chunks = []
    changes = []
    for name in sorted(before.keys() | after.keys()):
        left = before[name].read_bytes() if name in before else b''
        right = after[name].read_bytes() if name in after else b''
        if left == right:
            continue
        if b'\0' in left or b'\0' in right or max(len(left), len(right)) > 4 * 1024**2:
            raise ValueError('only bounded text source changes are supported')
        changes.append(name)
        a = left.decode('utf-8').splitlines(keepends=True)
        b = right.decode('utf-8').splitlines(keepends=True)
        for line in difflib.unified_diff(a, b, fromfile='a/'+name if name in before else '/dev/null',
                                         tofile='b/'+name if name in after else '/dev/null'):
            chunks.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    patch = ''.join(chunks).encode()
    if len(patch) > 20 * 1024**2:
        raise ValueError('patch exceeds evaluator limit')
    Path(destination).write_bytes(patch)
    return changes
