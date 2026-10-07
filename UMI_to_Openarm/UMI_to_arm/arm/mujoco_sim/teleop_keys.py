"""Sequence-numbered keyboard relay: slower arm cannot miss S/R events."""
import json
import os
from pathlib import Path

class KeyRelay:
    def __init__(self, path):
        self.path = Path(path)
        self.sequence = 0
        self.history = []
        self.received = 0

    def publish(self, keys):
        if not keys:
            return
        self.sequence += 1
        self.history.append({'sequence':self.sequence,'keys':keys})
        self.history = self.history[-256:]
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.history),encoding='utf-8')
        os.replace(temp,self.path)

    def consume(self):
        try:
            history=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return []
        keys=[]
        for event in history:
            if event['sequence'] > self.received:
                keys.extend(event['keys'])
                self.received=event['sequence']
        return keys
