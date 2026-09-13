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

### `cargo-test-coverage`
Runs `cargo llvm-cov test`, exports an LCOV coverage report, uploads the coverage artifact, and writes a coverage summary to the GitHub Actions Job Summary. Supports specifying packages, workspaces, features, and custom arguments.

```yaml
jobs:
  test-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Cargo Test Coverage
        uses: LittleTealeaf/github-actions/cargo-test-coverage@main
        with:
          toolchain: 'stable'
          packages: '' # optional space-separated list, e.g. "crate-a crate-b"
          workspace: 'false' # or 'true' to pass --workspace
          all-features: 'true'
          features: '' # optional feature flags, e.g. "feat1,feat2"
          all-targets: 'false'
          no-fail-fast: 'true'
          output-path: 'lcov.info'
          upload-artifact: 'true'
          summary: 'true'
```

---

## License
MIT
