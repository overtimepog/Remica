# Rebuild Command Added

## Overview
A new `rebuild` command has been added to `run.sh` that combines cleanup and build operations into a single convenient command.

## Usage
```bash
./run.sh rebuild
```

## What it does
1. **Cleanup Phase**:
   - Stops and removes all containers
   - Removes volumes
   - Clears Docker build cache
   - Shows reclaimed space

2. **Build Phase**:
   - Checks dependencies (Docker, Docker Compose)
   - Builds all containers from scratch with `--no-cache`
   - Shows build progress

## Benefits
- **One command** instead of two (`./run.sh cleanup` + `./run.sh build`)
- **Clean slate** ensures no cached layers or old configurations persist
- **Time saver** for development when you need to completely rebuild
- **Consistent state** after making significant changes to code or dependencies

## Example Output
```
[INFO] Starting rebuild process...
[INFO] Cleaning up containers and volumes...
Total reclaimed space: 737.9MB
[INFO] Cleanup completed!
[INFO] Checking dependencies...
[INFO] Dependencies check passed!
[INFO] Building containers...
[INFO] Containers built successfully!
[INFO] Rebuild completed successfully!
```

## When to Use
- After updating dependencies in `requirements.txt`
- When switching between branches with different configurations
- After making changes to `Dockerfile` or `docker-compose.yml`
- When experiencing strange behavior that might be cache-related
- Before deploying to ensure a clean build