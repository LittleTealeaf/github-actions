# GitHub Actions Collection

A collection of reusable composite GitHub Actions and workflows for CI/CD pipelines.

## Actions

### `cargo-clippy`
Runs `cargo clippy` with optional dependency caching and configurable toolchain and flags.

```yaml
- name: Run Cargo Clippy
  uses: LittleTealeaf/github-actions/cargo-clippy@main
  with:
    toolchain: 'stable'
    working-directory: '.'
    args: '--all-targets --all-features -- -D warnings'
    cache: 'true'
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
