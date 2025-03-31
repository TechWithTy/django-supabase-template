# CI/CD Workflows

This document outlines the CI/CD workflows used in the django-supabase-template project.

## Table of Contents
- [Overview](#overview)
- [Workflows](#workflows)
  - [CI/CD Pipeline](#cicd-pipeline)
  - [Deployment Pipeline](#deployment-pipeline)
  - [Security Scanning](#security-scanning)
- [GitHub Actions Permissions](#github-actions-permissions)
- [Environment Variables](#environment-variables)

## Overview

The project uses GitHub Actions for continuous integration and deployment. There are three main workflows:

1. **CI/CD Pipeline**: Lint code, run tests, and build Docker images
2. **Deployment Pipeline**: Deploy applications to production or staging environments
3. **Security Scanning**: Run security scans to identify vulnerabilities

## Workflows

### CI/CD Pipeline

**File**: `.github/workflows/ci-cd.yml`

**Triggered By**:
- Push to `main` or `develop` branches (excluding markdown files)
- Pull requests to `main` or `develop` branches (excluding markdown files)
- Manual dispatch

**Permissions**:
- `contents: read`
- `packages: write` (for pushing Docker images to GitHub Container Registry)

**Jobs**:

1. **Lint**
   - Runs code quality checks with `continue-on-error: true`
   - Tools: black, isort, flake8, mypy
   - Formats code automatically in pull requests
   - Outputs linting reports in JSON format

2. **Test**
   - Runs after linting completes
   - Sets up services: PostgreSQL, Redis
   - Configures environment variables for testing
   - Runs pytest with coverage reporting
   - Uses real Supabase connection for authentication tests

3. **Build**
   - Runs after testing completes (only on push to main/develop)
   - Builds Docker image using multi-stage Dockerfile
   - Tags and pushes to GitHub Container Registry (ghcr.io)
   - Uses Docker BuildX for efficient builds

### Deployment Pipeline

**File**: `.github/workflows/deploy.yml`

**Triggered By**:
- Push to `main` branch (production)
- Push to `develop` branch (staging)

**Permissions**:
- `contents: read`
- `packages: write` (for pushing Docker images)

**Jobs**:

1. **Deploy**
   - Connects to server via SSH
   - Pulls latest Docker image
   - Updates environment variables
   - Restarts services
   - Runs database migrations
   - Performs health checks

### Security Scanning

**File**: `.github/workflows/security-scan.yml`

**Triggered By**:
- Schedule (weekly)
- Push to `main` branch
- Manual dispatch

**Jobs**:

1. **Dependency Scanning**
   - Checks for vulnerable dependencies using tools like Safety

2. **Code Scanning**
   - Static analysis for security vulnerabilities
   - Uses tools like Bandit for Python

## GitHub Actions Permissions

Proper permissions are critical for the workflows to function correctly, especially for pushing to GitHub Container Registry:

```yaml
permissions:
  contents: read
  packages: write
```

These permissions allow the workflow to:
- Read repository contents
- Push Docker images to GitHub Container Registry (ghcr.io)

## Environment Variables

The workflows use the following environment variables:

### Database Configuration
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port

### Supabase Configuration
- `SUPABASE_URL`: URL of the Supabase instance
- `SUPABASE_ANON_KEY`: Anonymous key for Supabase
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key for Supabase
- `SUPABASE_JWT_SECRET`: JWT secret for Supabase authentication

### Redis Configuration
- `REDIS_PASSWORD`: Redis password
- `REDIS_DB`: Redis database number
- `REDIS_PORT`: Redis port
- `REDIS_URL`: Full Redis connection URL

### Deployment Configuration
- `DEPLOY_HOST`: Host to deploy to
- `DEPLOY_USER`: User to deploy as
- `DEPLOY_SSH_KEY`: SSH key for deployment
- `DEPLOY_PATH`: Path on server to deploy to
