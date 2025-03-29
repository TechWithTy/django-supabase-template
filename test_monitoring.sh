#!/bin/bash

# Start Docker containers
echo "Starting Docker containers..."
docker-compose up -d

# Allow services time to initialize
echo "Waiting for services to initialize..."
sleep 10

# Run the tests
echo "Running monitoring tests..."
docker-compose exec backend python manage.py test apps.monitoring.tests.test_docker_monitoring

# Display the results
echo "Tests completed."

# Optional: Show logs if there were errors
# docker-compose logs backend

# Optional: Stop containers when done
# echo "Stopping Docker containers..."
# docker-compose down
