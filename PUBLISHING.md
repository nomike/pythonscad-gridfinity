# Publishing setup

The workflows use GitHub's OpenID Connect identity and PyPI trusted publishing.
No PyPI API-token secret is required.

## One-time GitHub setup

1. Create public repository `nomike/pythonscad-gridfinity` with default branch
   `main`.
2. In **Settings → Environments**, create protected environments named
   `testpypi` and `pypi`.
3. Configure both environments with a required reviewer and restrict deployment
   branches to `main` and protected tags. This ensures a merged workflow change
   cannot publish without a separate approval. Do not add package-index secrets.
4. In **Settings → Actions → General**, allow GitHub Actions to create and
   approve pull requests so release-please can maintain its release PR.
5. Protect `main` and require the CI, pre-commit, and commit-message checks
   after their first successful runs.

Release creation and publishing are jobs in one workflow (`publish.yml`). This
avoids a personal access token solely to trigger a second workflow from a
`GITHUB_TOKEN`-created release.

Publishing jobs are scoped narrowly:

- Only `publish-development`, `publish-release-testpypi`, and
  `publish-release-pypi` request `id-token: write`.
- Those jobs run exclusively on guarded `push` events to `main` (or manual
  dispatch of the same workflow) and use protected environments.
- Pull-request workflows never publish and never receive `id-token: write`.

Development uploads are built directly from `main`. The `testpypi` environment
must therefore allow deployments from `main`.

## One-time TestPyPI setup

At <https://test.pypi.org/manage/account/publishing/>, add a pending trusted
publisher scoped to this repository, workflow, and environment:

- PyPI project name: `pythonscad-gridfinity`
- Owner: `nomike`
- Repository: `pythonscad-gridfinity`
- Workflow: `publish.yml`
- Environment: `testpypi`

The pending publisher can create the project on its first successful upload.
Every non-release push to `main` is built as a unique next-patch development
version with `skip-existing`.

## One-time PyPI setup

At <https://pypi.org/manage/account/publishing/>, add the same pending trusted
publisher with environment `pypi`. The release workflow publishes to TestPyPI
first and production PyPI second. Production uploads do **not** use
`skip-existing`.

Trusted publishers must match the workflow filename and environment name exactly.
Environment protection rules and required reviewers are enforced in GitHub, not
in this repository.

## Permanent forks

A fork owner should:

1. Change project URLs and author metadata in `pyproject.toml`.
2. Choose a unique distribution name; PyPI names are global.
3. Change badge and clone URLs in `README.md`.
4. Create matching protected GitHub environments.
5. Register trusted publishers using the fork owner, repository, workflow
   filename, and environment names.
6. Update this document's examples.

No workflow secrets contain the original owner's identity. The OIDC claim is
derived from the repository and environment at runtime.
