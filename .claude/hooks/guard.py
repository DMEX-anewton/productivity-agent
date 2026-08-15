#!/usr/bin/env python3
"""PreToolUse guard — blocks agent writes/deletes targeting data/ or audit/, and
shell-issued SQL that is not a plain read.

Defense-in-depth alongside the deny rules in .claude/settings.json: the deny
rules stop the file tools by path; this hook also catches shell commands that
would modify the protected folders. Exit code 2 = block the tool call (the
stderr message is shown to the agent so it understands why).

On SQL: the settings allowlist matches command prefixes, so it cannot tell a
SELECT from a DELETE inside `python foo.py`. This hook catches write statements
that appear *inline* in a shell command (sqlcmd -Q, python -c, ...). It is a net,
not a boundary. The real boundaries are, in order:
  1. Server-side grants — the connecting account holds db_datareader ONLY.
  2. `_assert_readonly()` inside run_query, which sees the actual query string.
"""
import json, re, sys

PROTECTED = re.compile(r'(^|[\s"\'=(/\\])(data|audit)[/\\]', re.IGNORECASE)
DESTRUCTIVE = re.compile(
    r'\b(rm|del|erase|rmdir|rd|move-item|remove-item|mv|copy-item\s+-force|'
    r'out-file|set-content|add-content|tee)\b|>{1,2}', re.IGNORECASE)

# Command looks like it is talking to a database.
SQL_CONTEXT = re.compile(
    r'\b(sqlcmd|osql|bcp|mssql-cli|sqlpackage|invoke-sqlcmd)\b|'
    r'(cursor|\.execute\(|pypyodbc|pyodbc|read_sql)', re.IGNORECASE)
# Two-word forms, so the words alone (in prose, identifiers, comments) don't trip it.
# _ID allows schema-qualified and bracketed names: dbo.PLC, [dbo].[PLC], #tmp.
_ID = r'[\w.\[\]#"`]+'
SQL_WRITE = re.compile(
    r'\b(INSERT\s+INTO|UPDATE\s+' + _ID + r'\s+SET|DELETE\s+FROM|MERGE\s+INTO|'
    r'TRUNCATE\s+TABLE|'
    r'(DROP|ALTER|CREATE)\s+(TABLE|VIEW|DATABASE|INDEX|SCHEMA|PROC|PROCEDURE|FUNCTION)|'
    r'GRANT\s+\w|REVOKE\s+\w|EXEC(UTE)?\s+' + _ID + r'|SP_\w+|'
    r'\sINTO\s+' + _ID + r'\s+FROM)\b',
    re.IGNORECASE)


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

    elif tool in ('Bash', 'PowerShell'):
        cmd = ti.get('command', '') or ''
        if PROTECTED.search(cmd) and DESTRUCTIVE.search(cmd):
            deny('BLOCKED by guard.py: this shell command appears to modify data/ or '
                 'audit/. Source data is read-only. Read operations are fine.')
        if SQL_CONTEXT.search(cmd):
            m = SQL_WRITE.search(cmd)
            if m:
                deny(f'BLOCKED by guard.py: SQL write statement {m.group(0).strip()!r} in a '
                     'shell command. Database access is SELECT/WITH only (CLAUDE.md rule 4). '
                     'Route queries through run_query(), which asserts read-only in-process.')
    sys.exit(0)


if __name__ == '__main__':
    main()
