# Docker Setup in CI/CD Pipeline

This document describes the Docker configuration used in the django-supabase-template CI/CD pipeline.

## Table of Contents
- [Overview](#overview)
- [Dockerfile Structure](#dockerfile-structure)
- [Multi-Stage Builds](#multi-stage-builds)
- [GitHub Container Registry](#github-container-registry)
- [Best Practices](#best-practices)

## Overview

The project uses Docker for containerization and GitHub Container Registry for image storage. The CI/CD pipeline builds, tags, and pushes Docker images automatically when code is pushed to the main or develop branches.

## Dockerfile Structure

### Production Dockerfile

**File**: `docker/Dockerfile.prod`

The production Dockerfile uses a multi-stage build process to create a smaller, more secure final image:

1. **Base Stage**
   - Uses Python 3.11 Alpine as the base image
   - Sets up environment variables and working directory
   - Installs system dependencies

2. **Dependencies Stage**
   - Copies and installs Python dependencies from requirements.txt
   - Uses pip and wheel for efficient package installation

3. **Final Stage**
   - Copies only the necessary files from previous stages
   - Sets up the application for production use
   - Configures proper permissions and user context
   - Sets the entrypoint for the container

## Multi-Stage Builds

Multi-stage builds provide several advantages in the CI/CD pipeline:

1. **Smaller Image Size**
   - Only necessary files are included in the final image
   - Development tools and build dependencies are excluded

2. **Improved Security**
   - Reduced attack surface with fewer components
   - No build tools or development dependencies in production

3. **Better Caching**
   - Dependency layers can be cached separately from application code
   - Faster builds when only application code changes

## GitHub Container Registry

The CI/CD pipeline pushes Docker images to GitHub Container Registry (ghcr.io) with appropriate permissions:

```yaml
permissions:
  contents: read
  packages: write
```

Key aspects of the GitHub Container Registry integration:

1. **Authentication**
   - Uses the GITHUB_TOKEN with packages:write permission
   - No need for additional credentials or secrets

2. **Tagging Strategy**
   - Tags images with the Git SHA for version tracking
   - Also tags with 'latest' for the most recent build
   - Different tags for main (production) and develop (staging) branches

3. **Image Naming**
   - Uses the repository name as the base for the image name
   - Follows the format: ghcr.io/{owner}/{repo}:{tag}

## Best Practices

The Docker setup in the CI/CD pipeline follows these best practices:

1. **Security**
   - Runs containers as non-root users
   - Minimizes installed packages
   - Keeps base images updated

2. **Performance**
   - Uses BuildX for efficient caching
   - Optimizes layer ordering for better caching
   - Combines commands to reduce layer count

3. **Maintainability**
   - Clear separation between development and production Dockerfiles
   - Documented build arguments and environment variables
   - Consistent naming conventions
