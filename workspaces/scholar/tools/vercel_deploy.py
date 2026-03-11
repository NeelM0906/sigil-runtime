#!/usr/bin/env python3
"""
Vercel Deployment Tool
Deploy web projects to Vercel with shareable URLs.

Usage:
    python3 vercel_deploy.py <project_dir>              # Deploy to preview
    python3 vercel_deploy.py <project_dir> --prod       # Deploy to production
    python3 vercel_deploy.py --list                     # List deployments
    python3 vercel_deploy.py --info <deployment_url>    # Get deployment info
"""

import os
import sys
import subprocess
import argparse

def load_token():
    """Load Vercel token from environment or .env file"""
    token = os.environ.get('VERCEL_TOKEN')
    if not token:
        env_path = os.path.expanduser('~/.openclaw/.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('VERCEL_TOKEN='):
                        token = line.strip().split('=', 1)[1]
                        break
    return token

TOKEN = load_token()

def run_vercel(*args):
    """Run vercel CLI command with token"""
    cmd = ['vercel', '--token', TOKEN] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def deploy(project_dir, prod=False):
    """Deploy a project to Vercel"""
    if not os.path.isdir(project_dir):
        print(f"Error: {project_dir} is not a directory")
        return False
    
    os.chdir(project_dir)
    
    args = ['--yes']  # Auto-confirm
    if prod:
        args.append('--prod')
    
    print(f"🚀 Deploying {project_dir}{'to production' if prod else ' (preview)'}...")
    
    cmd = ['vercel', '--token', TOKEN] + args
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    return result.returncode == 0

def list_deployments():
    """List recent deployments"""
    stdout, stderr, code = run_vercel('ls')
    if code == 0:
        print(stdout)
    else:
        print(f"Error: {stderr}")

def whoami():
    """Show current user"""
    stdout, stderr, code = run_vercel('whoami')
    if code == 0:
        print(f"✅ Connected as: {stdout.strip()}")
    else:
        print(f"❌ Not authenticated: {stderr}")

def main():
    parser = argparse.ArgumentParser(description='Vercel Deployment Tool')
    parser.add_argument('project', nargs='?', help='Project directory to deploy')
    parser.add_argument('--prod', action='store_true', help='Deploy to production')
    parser.add_argument('--list', action='store_true', help='List deployments')
    parser.add_argument('--whoami', action='store_true', help='Show current user')
    
    args = parser.parse_args()
    
    if not TOKEN:
        print("Error: VERCEL_TOKEN not found in environment or ~/.openclaw/.env")
        sys.exit(1)
    
    if args.whoami:
        whoami()
    elif args.list:
        list_deployments()
    elif args.project:
        deploy(args.project, prod=args.prod)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
