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
          workspaces: '' # optional space-separated list, e.g. "crate-a crate-b", or 'true' to pass --workspace
          features: '' # optional feature flags, e.g. "feat1,feat2" or 'all' for --all-features
          all-targets: 'false'
          no-fail-fast: 'true'
          output-path: 'lcov.info'
          artifact-name: 'lcov' # set to '' to disable upload
          summary: 'true'
```

### `cargo-doc-pages`
Builds Rust documentation (`cargo doc`), generates a root redirect `index.html` to the crate docs, sets up `.nojekyll`, packages the documentation, and deploys it to GitHub Pages.

> **Note**: Requires the following workflow permissions and concurrency settings:
> ```yaml
> permissions:
>   contents: read
>   pages: write
>   id-token: write
>
> concurrency:
>   group: "pages"
>   cancel-in-progress: false
> ```

```yaml
jobs:
  docs:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy-docs.outputs.page-url }}
    permissions:
      contents: read
      pages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Build & Deploy Docs
        id: deploy-docs
        uses: LittleTealeaf/github-actions/cargo-doc-pages@main
        with:
          crate-name: '' # optional: auto-detected from Cargo.toml if omitted
          toolchain: 'stable'
          args: '--no-deps --all-features --workspace'
          deploy: 'true'
```

### `uv-test-coverage`
Runs pytest with code coverage via `uv`, exports an LCOV coverage report, uploads the coverage artifact, and writes a coverage summary to the GitHub Actions Job Summary.

```yaml
jobs:
  test-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run UV Test Coverage
        uses: LittleTealeaf/github-actions/uv-test-coverage@main
        with:
          python-version: '3.12'
          uv-version: 'latest'
          working-directory: '.'
          args: '' # optional extra pytest arguments, e.g. "-v" or "--cov-fail-under=80"
          output-path: 'lcov.info'
          artifact-name: 'lcov' # set to '' to disable upload
          summary: 'true'
```

---

## Automated Releases

This repository includes an automated SemVer release workflow ([`.github/workflows/release.yml`](file:///.github/workflows/release.yml)). On push to `main`, it:
1. Runs the test suite across all actions and helper scripts.
2. Analyzes conventional commits since the previous git tag.
3. Automatically increments the semantic version (`major` for breaking changes, `minor` for `feat:`, `patch` for `fix:`/chores).
4. Generates a categorized markdown changelog, tags the commit, updates the floating major version tag (e.g. `v1`), and publishes a GitHub Release.

---

## License
MIT
