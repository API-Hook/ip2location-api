# Contributing

Thanks for helping improve this project.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

The full IP2Location CSV and generated SQLite database are intentionally not committed. Tests use a small temporary database fixture.

## Run tests

```powershell
pytest
```

## Pull requests

- Keep changes focused and include tests for behavior changes.
- Do not commit IP2Location data files, generated SQLite databases, secrets, virtual environments, or benchmark output.
- Update `README.md` when commands, configuration, or API behavior changes.
