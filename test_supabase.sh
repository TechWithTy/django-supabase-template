#!/bin/bash

# Script to test Supabase integration

echo "===== Testing Supabase Integration ====="

# Check if .env file exists
if [ ! -f ".env" ]; then
  echo "Error: .env file not found!"
  echo "Please create a .env file with your Supabase credentials."
  echo "You can use .env.example as a template."
  exit 1
fi

# Check if running in Docker or local environment
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker environment"
  cd /app
  python -m pytest apps/supabase/tests/ -v
else
  echo "Running in local environment"
  
  # Check if Pipenv is installed
  if command -v pipenv &> /dev/null; then
    echo "Using Pipenv for testing"
    pipenv run pytest backend/apps/supabase/tests/ -v
  else
    echo "Pipenv not found, using regular pytest"
    cd backend
    python -m pytest apps/supabase/tests/ -v
  fi
fi
