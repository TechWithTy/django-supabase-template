@echo off
echo ===== Testing Supabase Integration =====

:: Check if .env file exists
if not exist ".env" (
  echo Error: .env file not found!
  echo Please create a .env file with your Supabase credentials.
  echo You can use .env.example as a template.
  exit /b 1
)

:: Check if Pipenv is installed
where pipenv >nul 2>nul
if %ERRORLEVEL% == 0 (
  echo Using Pipenv for testing
  pipenv run pytest backend/apps/supabase/tests/ -v
) else (
  echo Pipenv not found, using regular pytest
  cd backend
  python -m pytest apps/supabase/tests/ -v
)
