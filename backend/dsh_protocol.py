"""Parser for the inspected @deepseek-ai/dsh 0.2.0-rc.2 headless JSONL contract."""
import json

class DshStream:
    def __init__(self):
        self.session_id = None
        self.final = None
        self.reason = None
        self.errors = []
        self.usage = []

    def feed(self, line):
        event = json.loads(line)
        if not isinstance(event, dict) or not isinstance(event.get('type'), str):
            raise ValueError('DSH event must be an object with a type')
        kind = event['type']
        if kind == 'session':
            identity = event.get('sessionId')
            if not isinstance(identity, str) or not identity:
                raise ValueError('Missing DSH session identity')
            if self.session_id and self.session_id != identity:
                raise ValueError('Session changed within one invocation')
            self.session_id = identity
        elif kind == 'final':
            self.final = event.get('text', '')
        elif kind == 'error':
            self.errors.append(event.get('message', 'DSH error'))
        elif kind == 'status':
            if event.get('phase') == 'turn_end':
                self.reason = event.get('reason')
            if event.get('phase') == 'step_end' and isinstance(event.get('usage'), dict):
                self.usage.append(event['usage'])
        return event

    def completed(self, returncode):
        return (returncode == 0 and self.session_id is not None and self.final is not None
                and isinstance(self.reason, dict) and self.reason.get('kind') == 'completed'
                and not self.errors)
