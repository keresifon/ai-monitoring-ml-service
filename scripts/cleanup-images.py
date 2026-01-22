#!/usr/bin/env python3
"""
Script to clean up old container images from GitHub Container Registry (GHCR).
Keeps a specified number of latest versions and specific tags.
"""

import argparse
import os
import sys
import requests
from datetime import datetime
from typing import List, Optional, Set


def get_package_versions(repository: str, github_token: str) -> tuple[List[dict], bool]:
    """
    Fetch all versions of a package from GHCR.
    
    Args:
        repository: Full repository path (e.g., 'ghcr.io/owner/repo')
        github_token: GitHub token for authentication
        
    Returns:
        Tuple of (list of package versions, is_user_owned)
    """
    # Extract owner and repo from repository path
    if repository.startswith('ghcr.io/'):
        repo_path = repository.replace('ghcr.io/', '')
    else:
        repo_path = repository
    
    owner, repo = repo_path.split('/', 1)
    
    # Try user endpoint first (for user-owned packages)
    # If that fails with 404, try org endpoint
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {github_token}',
    }
    
    # Try user endpoint first
    url = f"https://api.github.com/users/{owner}/packages/container/{repo}/versions"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json(), True  # is_user_owned = True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # Try organization endpoint
            url = f"https://api.github.com/orgs/{owner}/packages/container/{repo}/versions"
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json(), False  # is_user_owned = False
            except requests.exceptions.RequestException as e2:
                print(f"Error fetching package versions (tried both user and org endpoints): {e2}", file=sys.stderr)
                if hasattr(e2.response, 'text'):
                    print(f"Response: {e2.response.text}", file=sys.stderr)
                return [], True  # Default to user, but return empty list
        else:
            print(f"Error fetching package versions: {e}", file=sys.stderr)
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr)
            return [], True  # Default to user, but return empty list
    except requests.exceptions.RequestException as e:
        print(f"Error fetching package versions: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        return [], True  # Default to user, but return empty list


def parse_version_tags(version: dict) -> Set[str]:
    """Extract tags from a package version."""
    tags = set()
    metadata = version.get('metadata', {})
    container = metadata.get('container', {})
    version_tags = container.get('tags', [])
    tags.update(version_tags)
    return tags


def should_keep_version(version: dict, keep_tags: Set[str], keep_latest: int, version_index: int) -> bool:
    """
    Determine if a version should be kept.
    
    Args:
        version: Package version dict
        keep_tags: Set of tags that should always be kept
        keep_latest: Number of latest versions to keep
        version_index: Index of this version in the sorted list (0 = newest)
    """
    # Check if any tag matches the keep_tags
    version_tags = parse_version_tags(version)
    if version_tags.intersection(keep_tags):
        return True
    
    # Keep the N latest versions
    if version_index < keep_latest:
        return True
    
    return False


def delete_package_version(version_id: int, repository: str, github_token: str, is_user: bool = True) -> bool:
    """
    Delete a specific package version.
    
    Args:
        version_id: ID of the version to delete
        repository: Full repository path
        github_token: GitHub token for authentication
        is_user: Whether the package is user-owned (True) or org-owned (False)
    """
    # Extract owner and repo
    if repository.startswith('ghcr.io/'):
        repo_path = repository.replace('ghcr.io/', '')
    else:
        repo_path = repository
    
    owner, repo = repo_path.split('/', 1)
    
    # Use appropriate endpoint based on ownership
    if is_user:
        url = f"https://api.github.com/users/{owner}/packages/container/{repo}/versions/{version_id}"
    else:
        url = f"https://api.github.com/orgs/{owner}/packages/container/{repo}/versions/{version_id}"
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {github_token}',
    }
    
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error deleting version {version_id}: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description='Clean up old container images from GHCR')
    parser.add_argument('--repository', required=True,
                       help='Container repository path (e.g., ghcr.io/owner/repo)')
    parser.add_argument('--keep-latest', type=int, default=5,
                       help='Number of latest versions to keep (default: 5)')
    parser.add_argument('--keep-tags', default='latest',
                       help='Comma-separated tags to always keep (default: latest)')
    parser.add_argument('--github-token',
                       help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    github_token = args.github_token or os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Error: GitHub token required (--github-token or GITHUB_TOKEN env var)", file=sys.stderr)
        sys.exit(1)
    
    keep_tags = set(tag.strip() for tag in args.keep_tags.split(','))
    
    print(f"Repository: {args.repository}")
    print(f"Keep latest: {args.keep_latest} versions")
    print(f"Always keep tags: {', '.join(keep_tags)}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    # Fetch all versions
    print("Fetching package versions...")
    versions, is_user_owned = get_package_versions(args.repository, github_token)
    
    if not versions:
        print("No versions found or error fetching versions.")
        sys.exit(1)
    
    ownership_type = "user" if is_user_owned else "organization"
    print(f"Package ownership: {ownership_type}")
    
    print(f"Found {len(versions)} versions")
    print()
    
    # Sort versions by creation date (newest first)
    versions.sort(key=lambda v: v.get('created_at', ''), reverse=True)
    
    # Determine which versions to delete
    to_delete = []
    to_keep = []
    
    for index, version in enumerate(versions):
        version_id = version.get('id')
        created_at = version.get('created_at', 'unknown')
        tags = parse_version_tags(version)
        tags_str = ', '.join(tags) if tags else '(no tags)'
        
        if should_keep_version(version, keep_tags, args.keep_latest, index):
            to_keep.append((version_id, created_at, tags_str))
        else:
            to_delete.append((version_id, created_at, tags_str))
    
    # Print summary
    print("=" * 80)
    print(f"VERSIONS TO KEEP: {len(to_keep)}")
    print("=" * 80)
    for version_id, created_at, tags in to_keep:
        print(f"  ID: {version_id:12} | Created: {created_at} | Tags: {tags}")
    
    print()
    print("=" * 80)
    print(f"VERSIONS TO DELETE: {len(to_delete)}")
    print("=" * 80)
    for version_id, created_at, tags in to_delete:
        print(f"  ID: {version_id:12} | Created: {created_at} | Tags: {tags}")
    
    print()
    
    # Delete versions if not dry run
    if args.dry_run:
        print("DRY RUN MODE: No versions were actually deleted.")
        print("Run without --dry-run to delete these versions.")
    else:
        if not to_delete:
            print("No versions to delete.")
            sys.exit(0)
        
        print(f"Deleting {len(to_delete)} versions...")
        deleted = 0
        failed = 0
        
        for version_id, created_at, tags in to_delete:
            if delete_package_version(version_id, args.repository, github_token, is_user_owned):
                print(f"  ✓ Deleted version {version_id} ({tags})")
                deleted += 1
            else:
                print(f"  ✗ Failed to delete version {version_id} ({tags})")
                failed += 1
        
        print()
        print(f"Summary: {deleted} deleted, {failed} failed")
        
        if failed > 0:
            sys.exit(1)


if __name__ == '__main__':
    main()
