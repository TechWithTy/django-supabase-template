@echo off
echo Starting Docker containers...
docker-compose up -d

echo Waiting for services to initialize...
timeout /t 10 /nobreak

echo Running monitoring tests...
docker-compose exec backend python manage.py test apps.monitoring.tests.test_docker_monitoring

echo Tests completed.

:: Optional: Show logs if there were errors
:: docker-compose logs backend

:: Optional: Stop containers when done
:: echo Stopping Docker containers...
:: docker-compose down
