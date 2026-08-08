# Versioning and releases

This project follows [Semantic Versioning](https://semver.org/) and uses
[release-please](https://github.com/googleapis/release-please).

Merging Conventional Commits into `main` causes release-please to create or
update a release pull request. The pull request updates `CHANGELOG.md` and the
version in `pyproject.toml`.

- `fix:` produces a patch release.
- `feat:` produces a minor release.
- `<type>!:` (for example, `feat!:`) or a `BREAKING CHANGE:` footer produces a
  major release.
- Other accepted types appear in history but normally do not change version.

When the release pull request is merged, release-please creates the Git tag and
GitHub release. The same workflow builds one wheel and source distribution,
attaches them to the GitHub release, publishes to TestPyPI, and then publishes
to PyPI after the configured environment approval.

Ordinary pushes to `main` build a unique `.devN` version for TestPyPI. Package
index files are immutable, so the workflow never attempts to overwrite an
existing version on PyPI; TestPyPI development uploads use `skip-existing`.

The `v0.1.0` tag is the pre-packaging source baseline. The first release built
and published by this automation will be `v0.2.0`.
