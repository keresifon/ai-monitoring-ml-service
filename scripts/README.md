# Image Tag Update Script

This script automatically updates the image tag in `charts/values.yaml` when a new tag is created, preparing the chart for deployment.

## Usage

### Manual Update

```bash
# Check what the latest tag is (without updating)
python scripts/update-image-tag.py --check-only

# Update the values.yaml file to latest tag
python scripts/update-image-tag.py --update

# Update to a specific tag
python scripts/update-image-tag.py --update --tag v1.2.3

# Get just the latest tag value
python scripts/update-image-tag.py --get-latest
```

### With Custom Repository

```bash
python scripts/update-image-tag.py --repository ghcr.io/your-org/your-repo --update
```

### With GitHub Token (for private repos or rate limiting)

```bash
export GITHUB_TOKEN=your_token_here
python scripts/update-image-tag.py --update
```

## GitHub Actions Workflow

The `.github/workflows/update-image-tag.yml` workflow automatically updates `values.yaml` **after** the Docker image is built and pushed to the registry. This ensures the image is available before updating the deployment configuration.

### Trigger Flow

1. **Primary: Repository Dispatch** (from `ci-cd.yml` docker-build job)
   - When a tag is pushed (e.g., `v1.2.3`), the CI/CD workflow builds and pushes the Docker image
   - After the image is successfully pushed, it triggers this workflow via `repository_dispatch`
   - This is the preferred method as it guarantees the image is available

2. **Fallback: Workflow Run** (after CI/CD completes)
   - Triggers after the CI/CD workflow completes successfully
   - Extracts the tag from the workflow run context
   - Used as a backup if repository_dispatch doesn't work

3. **Release Events** - Triggers on `release: published` or `release: created` events

4. **Manual Trigger** - Can be manually triggered with an optional tag input

### How It Works

1. You push a tag: `git tag v1.2.3 && git push origin v1.2.3`
2. CI/CD workflow runs and builds the Docker image
3. After the image is pushed, the docker-build job triggers the update workflow
4. The update workflow extracts the tag (removes 'v' prefix: `1.2.3`)
5. Updates `charts/values.yaml` with the new tag
6. Commits and pushes directly to the branch (ready for deployment)

### Setup

1. **Update the repository path** in `charts/values.yaml`:
   ```yaml
   image:
     repository: ghcr.io/YOUR-ORG/YOUR-REPO
   ```

2. **For repository dispatch triggers** (optional, but recommended):
   - If you get "Resource not accessible by integration" errors, create a Personal Access Token (PAT):
     - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
     - Create a token with `repo` scope
     - Add it as a secret named `REPO_DISPATCH_TOKEN` in your repository
   - The workflow will use this token if available, otherwise fall back to `GITHUB_TOKEN`
   - **Note**: The `workflow_run` fallback will still work even if repository_dispatch fails

3. **Workflow permissions**: 
   - The `docker-build` job needs `contents: write` permission (already configured)
   - The `update-image-tag` workflow needs `contents: write` permission (already configured)

## How It Works

1. The script queries the GHCR API to get all available tags
2. It filters out the 'latest' tag and finds the most recent semantic version
3. It compares with the current tag in `values.yaml`
4. If different, it updates the file (or creates a PR in GitHub Actions)

## Requirements

- Python 3.7+
- `pyyaml` package
- `requests` package

Install dependencies:
```bash
pip install pyyaml requests
```
