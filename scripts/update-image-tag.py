#!/usr/bin/env python3
"""
Script to update the image tag in charts/values.yaml based on the latest tag
from GitHub Container Registry (GHCR).
"""

import argparse
import os
import re
import sys
import yaml
import requests
from pathlib import Path
from typing import Optional


def get_latest_tag_from_ghcr(repository: str, github_token: Optional[str] = None) -> Optional[str]:
    """
    Fetch the latest tag from GitHub Container Registry.
    
    Args:
        repository: Full repository path (e.g., 'ghcr.io/owner/repo')
        github_token: Optional GitHub token for authentication
        
    Returns:
        Latest tag or None if not found
    """
    # Extract owner and repo from repository path
    # Format: ghcr.io/owner/repo or owner/repo
    if repository.startswith('ghcr.io/'):
        repo_path = repository.replace('ghcr.io/', '')
    else:
        repo_path = repository
    
    owner, repo = repo_path.split('/', 1)
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }
    
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    # Try user endpoint first (for user-owned packages)
    # If that fails with 404, try org endpoint
    url = f"https://api.github.com/users/{owner}/packages/container/{repo}/versions"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        versions = response.json()
        if not versions:
            print(f"No versions found for {repository}", file=sys.stderr)
            return None
        
        # Get the most recent version (first in the list)
        # Filter out 'latest' tag and get the most recent semantic version or tag
        tags = []
        for version in versions:
            metadata = version.get('metadata', {})
            container = metadata.get('container', {})
            version_tags = container.get('tags', [])
            tags.extend(version_tags)
        
        # Remove 'latest' and get the most recent tag
        tags = [t for t in tags if t != 'latest']
        
        if not tags:
            print(f"No tags found (excluding 'latest') for {repository}", file=sys.stderr)
            return None
        
        # Sort tags - prefer semantic versions, then lexicographic
        def tag_sort_key(tag):
            # Try to parse as semantic version
            parts = tag.split('.')
            if len(parts) >= 3:
                try:
                    return tuple(int(p) for p in parts[:3])
                except ValueError:
                    pass
            return (0, 0, 0, tag)
        
        latest_tag = sorted(tags, key=tag_sort_key, reverse=True)[0]
        return latest_tag
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # Try organization endpoint
            url = f"https://api.github.com/orgs/{owner}/packages/container/{repo}/versions"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                versions = response.json()
                if not versions:
                    print(f"No versions found for {repository}", file=sys.stderr)
                    return None
                
                # Get the most recent version (first in the list)
                tags = []
                for version in versions:
                    metadata = version.get('metadata', {})
                    container = metadata.get('container', {})
                    version_tags = container.get('tags', [])
                    tags.extend(version_tags)
                
                # Remove 'latest' and get the most recent tag
                tags = [t for t in tags if t != 'latest']
                
                if not tags:
                    print(f"No tags found (excluding 'latest') for {repository}", file=sys.stderr)
                    return None
                
                # Sort tags - prefer semantic versions, then lexicographic
                def tag_sort_key(tag):
                    parts = tag.split('.')
                    if len(parts) >= 3:
                        try:
                            return tuple(int(p) for p in parts[:3])
                        except ValueError:
                            pass
                    return (0, 0, 0, tag)
                
                latest_tag = sorted(tags, key=tag_sort_key, reverse=True)[0]
                return latest_tag
            except requests.exceptions.RequestException as e2:
                print(f"Error fetching tags from GHCR (tried both user and org endpoints): {e2}", file=sys.stderr)
                return None
        else:
            print(f"Error fetching tags from GHCR: {e}", file=sys.stderr)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tags from GHCR: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return None


def get_current_tag(values_file: Path) -> Optional[str]:
    """Get the current tag from values.yaml."""
    try:
        with open(values_file, 'r') as f:
            content = yaml.safe_load(f)
            return content.get('image', {}).get('tag')
    except Exception as e:
        print(f"Error reading values.yaml: {e}", file=sys.stderr)
        return None


def update_values_file(values_file: Path, new_tag: str) -> bool:
    """Update the tag in values.yaml file."""
    try:
        with open(values_file, 'r') as f:
            content = f.read()
        
        # Replace the tag line
        pattern = r'(tag:\s*["\']?)([^"\'\s]+)(["\']?)'
        replacement = f'\\g<1>{new_tag}\\g<3>'
        updated_content = re.sub(pattern, replacement, content)
        
        if updated_content == content:
            print(f"Warning: Tag not found or already set to {new_tag}", file=sys.stderr)
            return False
        
        with open(values_file, 'w') as f:
            f.write(updated_content)
        
        return True
    except Exception as e:
        print(f"Error updating values.yaml: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description='Update image tag in values.yaml')
    parser.add_argument('--values-file', default='charts/values.yaml',
                       help='Path to values.yaml file')
    parser.add_argument('--repository', 
                       default='ghcr.io/OWNER/ai-monitoring-frontend',
                       help='Container repository path')
    parser.add_argument('--github-token', 
                       help='GitHub token for authentication (or set GITHUB_TOKEN env var)')
    parser.add_argument('--update', action='store_true',
                       help='Update the values.yaml file')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check, do not update')
    parser.add_argument('--get-latest', action='store_true',
                       help='Print latest tag and exit')
    parser.add_argument('--tag',
                       help='Specific tag to use instead of fetching latest')
    
    args = parser.parse_args()
    
    values_file = Path(args.values_file)
    if not values_file.exists():
        print(f"Error: {values_file} not found", file=sys.stderr)
        sys.exit(1)
    
    github_token = args.github_token or os.environ.get('GITHUB_TOKEN')
    
    # Get repository from values.yaml if not provided
    if args.repository == 'ghcr.io/OWNER/ai-monitoring-frontend':
        try:
            with open(values_file, 'r') as f:
                content = yaml.safe_load(f)
                repo = content.get('image', {}).get('repository')
                if repo:
                    args.repository = repo
        except Exception:
            pass
    
    # Use provided tag or fetch latest
    if args.tag:
        latest_tag = args.tag
    else:
        latest_tag = get_latest_tag_from_ghcr(args.repository, github_token)
        
        if not latest_tag:
            print("Error: Could not fetch latest tag", file=sys.stderr)
            sys.exit(1)
    
    if args.get_latest:
        print(latest_tag)
        sys.exit(0)
    
    current_tag = get_current_tag(values_file)
    
    print(f"Current tag: {current_tag}")
    print(f"Latest tag: {latest_tag}")
    
    if current_tag == latest_tag:
        print("Tags are already in sync")
        sys.exit(0)
    
    if args.check_only:
        print(f"Update needed: {current_tag} -> {latest_tag}")
        sys.exit(0)
    
    if args.update:
        if update_values_file(values_file, latest_tag):
            print(f"Successfully updated tag to {latest_tag}")
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print(f"Use --update to update the tag from {current_tag} to {latest_tag}")


if __name__ == '__main__':
    main()
