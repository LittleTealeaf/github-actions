# GitHub Actions Collection

A collection of reusable composite GitHub Actions and workflows for CI/CD pipelines.

## Actions

### `cargo-clippy`
Runs `cargo clippy` with JSON message formatting, SARIF conversion via `clippy-sarif` / `sarif-fmt`, and uploads the results to GitHub Code Scanning (SARIF).

> **Note**: If `upload-sarif` is enabled (default `true`), the workflow calling this action requires the `security-events: write` permission.

```yaml
jobs:
  clippy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - name: Run Cargo Clippy
        uses: LittleTealeaf/github-actions/cargo-clippy@main
        with:
          toolchain: 'stable'
          args: '--all --no-deps --all-features'
          clippy-args: '-W clippy::todo'
```

### `cargo-lint` / `cargo-fmt`
Runs `cargo fmt --check` to verify code formatting.

```yaml
- name: Run Cargo Format Check
  uses: LittleTealeaf/github-actions/cargo-lint@main
  with:
    toolchain: 'stable'
    working-directory: '.'
    args: '--all -- --check'
```

### `cargo-test`
Runs `cargo test` with dependency caching and configurable flags.

```yaml
- name: Run Cargo Tests
  uses: LittleTealeaf/github-actions/cargo-test@main
  with:
    toolchain: 'stable'
    working-directory: '.'
    args: '--all-targets --all-features'
    cache: 'true'
```

---

## License
MIT
