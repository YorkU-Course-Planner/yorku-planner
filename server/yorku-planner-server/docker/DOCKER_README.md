# Running YorkU Planner Server with Docker

This guide explains how to run the YorkU Planner Spring Boot application using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose installed (usually comes with Docker Desktop)

## Quick Start

### Option 1: Using the provided script (Recommended)

```bash
# Navigate to the server directory
cd server/yorku-planner-server

# Run the application
./docker-run.sh
```

### Option 2: Using Docker Compose directly

```bash
# Navigate to the server directory
cd server/yorku-planner-server

# Build and start the application
docker-compose up --build
```

### Option 3: Using Docker commands directly

```bash
# Navigate to the server directory
cd server/yorku-planner-server

# Build the Docker image
docker build -t yorku-planner-server .

# Run the container
docker run -p 8080:8080 yorku-planner-server
```

## Accessing the Application

Once the container is running, you can access:

- **Main Application**: http://localhost:8080
- **H2 Database Console**: http://localhost:8080/h2-console
  - JDBC URL: `jdbc:h2:mem:testdb`
  - Username: `sa`
  - Password: `password`

## Docker Commands Reference

### Build the image
```bash
docker build -t yorku-planner-server .
```

### Run the container
```bash
docker run -p 8080:8080 yorku-planner-server
```

### Run in detached mode
```bash
docker run -d -p 8080:8080 --name yorku-planner yorku-planner-server
```

### Stop the container
```bash
docker stop yorku-planner
```

### View logs
```bash
docker logs yorku-planner
```

### Execute commands in running container
```bash
docker exec -it yorku-planner /bin/bash
```

## Docker Compose Commands

### Start services
```bash
docker-compose up
```

### Start services in detached mode
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs
```

### Rebuild and start
```bash
docker-compose up --build
```

## Configuration

The application uses the following default configuration:

- **Port**: 8080
- **Database**: H2 in-memory database
- **JVM Options**: -Xmx512m -Xms256m

You can modify these settings by:

1. Editing the `docker-compose.yml` file
2. Setting environment variables
3. Mounting a custom `application.properties` file

## Troubleshooting

### Port already in use
If port 8080 is already in use, change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8081:8080"  # Maps host port 8081 to container port 8080
```

### Memory issues
Adjust JVM memory settings in `docker-compose.yml`:
```yaml
environment:
  - JAVA_OPTS=-Xmx1g -Xms512m
```

### Build failures
If the build fails, try:
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

## Development with Docker

For development, you can mount your source code as a volume:

```yaml
volumes:
  - ./src:/app/src
  - ./pom.xml:/app/pom.xml
```

This allows you to make changes to your code without rebuilding the entire image.

## Production Considerations

For production deployment:

1. Use a production-ready database (PostgreSQL, MySQL, etc.)
2. Configure proper logging
3. Set up health checks
4. Use environment variables for sensitive configuration
5. Consider using Docker Swarm or Kubernetes for orchestration 