#!/usr/bin/env python3
"""Wrapper script for Docker-based CLI execution"""

import os
import sys
import subprocess

def main():
    """Launch the CLI in a Docker-friendly way"""
    # Check if we're in a Docker container
    if os.path.exists('/.dockerenv'):
        # We're in Docker, run the main application directly
        from main import main as cli_main
        cli_main()
    else:
        # We're outside Docker, use docker exec
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = [
            'docker-compose',
            '-f', os.path.join(script_dir, 'docker-compose.yml'),
            '-p', 'real-estate-chat-agent',
            'exec',
            '-it',
            'app',
            'python', '-m', 'src.main'
        ]
        subprocess.run(cmd)

if __name__ == "__main__":
    main()