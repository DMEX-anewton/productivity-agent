#!/usr/bin/env python3
"""PostToolUse audit — appends one JSON line per tool call to audit/audit-log.jsonl.

The audit folder is git-ignored (stays on the analyst's machine) and write-protected
from the agent itself; this hook runs outside the agent's tool sandbox, which is what
makes the log append-only in practice.
"""
import json, os, sys
from datetime import datetime

def main():
    try:
        evt = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never break the agent over logging
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    audit_dir = os.path.join(repo, 'audit')
    try:
        os.makedirs(audit_dir, exist_ok=True)
        rec = {
            'ts': datetime.now().astimezone().isoformat(timespec='seconds'),
            'session_id': evt.get('session_id'),
            'tool': evt.get('tool_name'),
            'input': evt.get('tool_input'),
        }
        with open(os.path.join(audit_dir, 'audit-log.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, default=str) + '\n')
    except Exception:
        pass
    sys.exit(0)

if __name__ == '__main__':
    main()
