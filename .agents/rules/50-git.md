# Git and Change Hygiene

- MUST inspect `git status` and the relevant diff before editing; preserve unrelated user work.
- MUST keep generated/runtime files out of commits: `.env`, `*.pkl`, `*.joblib`, `temp/`, `output/`, `logs/`, `models/*.pkl`, media, `__pycache__`, `.venv`.
- MUST NOT use `git reset --hard`, `git clean -fd`, force-push, or rewrite history without explicit confirmation.
- MUST NOT amend or rebase commits that were already pushed.
- MUST keep commits scoped and descriptive; do not mix refactors, formatting, and behavior changes without need.
- MUST report the exact gate/test commands and results in the final response.
