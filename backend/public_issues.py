"""Resolve only allowlisted public issue statements for the task catalog."""
import json
import re
from pathlib import Path
from .proto_config import PROTO

ROOT = Path(__file__).resolve().parents[1]


PROTO_TASKS = PROTO / 'tasks'


def _public_task_root(task_id):
    """Find a task folder by its public task.json ID; never inspect private/."""
    try:
        task_base = PROTO_TASKS.resolve(strict=True)
        for candidate in task_base.iterdir():
            if candidate.is_symlink() or not candidate.is_dir() or not candidate.name.startswith('task_'):
                continue
            manifest = candidate / 'task.json'
            if manifest.is_symlink() or not manifest.is_file():
                continue
            resolved_manifest = manifest.resolve(strict=True)
            if not resolved_manifest.is_relative_to(task_base) or resolved_manifest.stat().st_size > 65536:
                continue
            payload = json.loads(resolved_manifest.read_text(encoding='utf-8'))
            if payload.get('task_id') == task_id:
                visible = candidate / 'visible'
                resolved_visible = visible.resolve(strict=True)
                if resolved_visible.is_relative_to(candidate.resolve(strict=True)) and resolved_visible.is_dir():
                    return resolved_visible
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return None


def _public_task_readme(task_id):
    """Read only the README belonging to a public task directory."""
    visible_root = _public_task_root(task_id)
    if visible_root is None:
        return None
    try:
        task_root = visible_root.parent.resolve(strict=True)
        task_base = PROTO_TASKS.resolve(strict=True)
        readme = task_root / 'README.md'
        resolved = readme.resolve(strict=True)
        if (not readme.is_symlink() and resolved.is_relative_to(task_base)
                and resolved.is_file() and resolved.stat().st_size <= 256 * 1024):
            return resolved.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        pass
    return None


def _clean_issue(markdown):
    paragraphs = re.split(r'\n\s*\n', markdown.replace('\r\n', '\n').strip())
    title = ''
    body_paragraphs = []

    for paragraph in paragraphs:
        lines = paragraph.strip().splitlines()
        if not lines:
            continue
        if lines[0].startswith('# '):
            heading = lines[0][2:].strip()
            if not title and not re.fullmatch(r'OCCT issue #\d+', heading, re.I):
                title = re.sub(r'^Issue\s+#\d+\s*[—:-]\s*', '', heading, flags=re.I)
            lines = lines[1:]
            if not lines:
                continue
        if lines[0].strip().lower().startswith('title:'):
            title = ' '.join([lines[0].split(':', 1)[1].strip(), *(line.strip() for line in lines[1:])]).strip()
            continue
        text = '\n'.join(lines)
        # Upstream fix references are evaluation hints; omit that paragraph tail.
        text = re.sub(r'(?is)\s*Upstream relation:.*$', '', text).strip()
        if text:
            body_paragraphs.append(text)

    body = '\n\n'.join(body_paragraphs).strip()
    summary = ''
    for paragraph in body_paragraphs:
        if paragraph.startswith('```'):
            continue
        summary = re.sub(r'\s+', ' ', paragraph).strip()
        break
    return title, summary, body


def enrich_task(task):
    """Add the public task README and issue text without touching private paths."""
    # Catalog tasks already contain the immutable, versioned public statements.
    # Never replace them with a legacy checkout's files or hidden provenance.
    if task.get('source_id') and task.get('evaluation_suite'):
        return task
    task_root = _public_task_root(task.get('id'))
    if task_root is None:
        return task
    enriched = {**task, 'issues': []}
    readme = _public_task_readme(task.get('id'))
    if readme is not None:
        readme = re.sub(r'(?is)Upstream relation:.*?(?:[.]|$)', '', readme)
        readme = re.sub(r'(?is)The public upstream fix references.*?(?:\n\n|$)', '', readme)
        enriched['readme'] = readme
    for issue in task.get('issues', []):
        item = dict(issue)
        match = re.fullmatch(r'occt-(\d+)', str(issue.get('id', '')))
        if match and issue.get('visibility') == 'public':
            issue_file = task_root / f"issue_{match.group(1)}" / 'issue.md'
            try:
                resolved = issue_file.resolve(strict=True)
                if (not issue_file.is_symlink() and resolved.is_relative_to(task_root)
                        and resolved.is_file() and resolved.stat().st_size <= 65536):
                    title, summary, body = _clean_issue(resolved.read_text(encoding='utf-8'))
                    item.update(number=match.group(1), title=title or item.get('title', issue['id']),
                                summary=summary, body=body)
            except (OSError, UnicodeError):
                pass
        enriched['issues'].append(item)
    return enriched
