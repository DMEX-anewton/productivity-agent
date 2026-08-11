# DME Express — Analyst Productivity Agent

Shared "brain" for the DME Express analyst agents: instructions (CLAUDE.md),
safety rails (.claude/), the analysis library and notebook templates (analysis/),
and the running insights/questions exchange (insights/).

**Analysts:** follow the setup document (DME Express Analyst Agent Setup v5) —
do not configure anything by hand.

**One command every fresh clone must run** (enables the output-stripping + PHI
pre-commit gate; git does not sync hooks automatically):

    git config core.hooksPath .githooks

Folder map: `data/` local-only extracts (git-ignored) · `outputs/` local-only
generated reports (git-ignored) · `audit/` local-only agent audit log
(git-ignored) · `analysis/` committed notebooks + shared library · `insights/`
shared findings and question backlogs · `docs/` procedures (incl. secrets-setup).
