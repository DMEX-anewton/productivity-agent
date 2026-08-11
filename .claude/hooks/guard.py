#!/usr/bin/env python3
"""PreToolUse guard — blocks agent writes/deletes targeting data/ or audit/.

Defense-in-depth alongside the deny rules in .claude/settings.json: the deny
rules stop the file tools by path; this hook also catches Bash commands that
would modify the protected folders. Exit code 2 = block the tool call (the
stderr message is shown to the agent so it understands why).
"""
import json, re, sys

PROTECTED = re.compile(r'(^|[\s"\'=(/\\])(data|audit)[/\\]', re.IGNORECASE)
DESTRUCTIVE = re.compile(
    r'\b(rm|del|erase|rmdir|rd|move-item|remove-item|mv|copy-item\s+-force|'
    r'out-file|set-content|add-content|tee)\b|>{1,2}', re.IGNORECASE)

def deny(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

def main():
    try:
        evt = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # malformed event: do not block, permissions deny-list still applies
    tool = evt.get('tool_name', '') or ''
    ti = evt.get('tool_input', {}) or {}

    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        path = (ti.get('file_path') or ti.get('notebook_path') or '')
        norm = '/' + path.replace('\\', '/').lstrip('/')
        if re.search(r'/(data|audit)/', norm, re.IGNORECASE):
            deny(f'BLOCKED by guard.py: {tool} may not touch data/ or audit/ ({path}). '
                 'Source data is read-only; the audit log is append-only via hook.')

    elif tool == 'Bash':
        cmd = ti.get('command', '') or ''
        if PROTECTED.search(cmd) and DESTRUCTIVE.search(cmd):
            deny('BLOCKED by guard.py: this shell command appears to modify data/ or '
                 'audit/. Source data is read-only. Read operations are fine.')
    sys.exit(0)

if __name__ == '__main__':
    main()
