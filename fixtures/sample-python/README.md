# Sample Python Test Fixture

This fixture is a minimal Python project used for testing GitHub Actions workflows (such as `uv-test-coverage`).

## Usage

Run tests with coverage using `uv`:

```bash
uv run pytest --cov=src --cov-report=term --cov-report=json:coverage.json
```
