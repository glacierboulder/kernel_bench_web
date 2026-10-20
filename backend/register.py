"""Register public manifests; private evaluator paths must never enter this catalog."""
import argparse
import json
from pathlib import Path
from .app import db

BANNED = {'private', 'hidden_issue', 'evaluator_path', 'secret', 'api_key'}

def register(item):
    item = dict(item)
    item.setdefault('tags', [])
    item.setdefault('description', '')
    item.setdefault('required_output', ['patch', 'report'])
    item.setdefault('execution_mode', 'joint')
    if isinstance(item.get('issues'), list):
        item['issues'] = [dict(i, title=i.get('title', i.get('id', ''))) for i in item['issues']]
    required = {'id', 'version', 'title', 'kind', 'base_commit', 'issues', 'budget', 'has_hidden_checks'}
    if not required <= item.keys():
        raise ValueError('题目字段不完整')
    if item['kind'] not in {'single', 'group', 'active'} or not item['issues']:
        raise ValueError('无效题目类型或空问题组')
    if item['budget'].get('scope') != 'group':
        raise ValueError('当前支持全组共享预算')
    identifiers = [i['id'] for i in item['issues']]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('issue 成员重复')
    if any(i.get('visibility') != 'public' for i in item['issues']):
        raise ValueError('公开目录不能登记隐藏成员')
    def inspect(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in BANNED:
                    raise ValueError('公开清单含私有字段')
                inspect(v)
        elif isinstance(value, list):
            for v in value:
                inspect(v)
    inspect(item)
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
    with db() as c:
        old = c.execute('SELECT payload FROM tasks WHERE id=? AND version=?', (item['id'], item['version'])).fetchone()
        if old and old['payload'] != payload:
            raise ValueError('题目版本已存在且内容不同；请增加版本号')
        c.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?)', (item['id'], item['version'], payload))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    value = json.loads(args.manifest.read_text())
    for item in value if isinstance(value, list) else [value]:
        register(item)
    print('题目注册完成')
