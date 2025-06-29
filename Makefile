.PHONY: build up down clean test logs status

# Build images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start the system
up: build
	@echo "Starting load balancer system..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 15
	@echo "Load balancer should be available at http://localhost:5000"
	@echo "Testing connection..."
	@timeout 30 bash -c 'until curl -sf http://localhost:5000/rep > /dev/null; do sleep 2; done' || echo "Warning: Service may not be ready yet"

# Stop the system
down:
	@echo "Stopping load balancer system..."
	docker-compose down
	@echo "Cleaning up orphaned containers..."
	docker container prune -f

# Clean everything
clean: down
	@echo "Cleaning up images and containers..."
	docker rmi -f load-balancer-project_server-build:latest 2>/dev/null || true
	docker rmi -f $$(docker images -q load-balancer-project_load-balancer) 2>/dev/null || true
	docker system prune -f

# Basic functionality test
test:
	@echo "Testing load balancer endpoints..."
	@echo "1. Testing /rep endpoint:"
	@curl -s http://localhost:5000/rep | python3 -m json.tool || echo "Failed"
	@echo "\n2. Testing /home endpoint:"
	@curl -s http://localhost:5000/home | python3 -m json.tool || echo "Failed"
	@echo "\n3. Testing /add endpoint:"
	@curl -s -X POST http://localhost:5000/add -H "Content-Type: application/json" -d '{"n": 1}' | python3 -m json.tool || echo "Failed"

# View logs
logs:
	docker-compose logs -f

# Show container status
status:
	@echo "=== Docker Compose Services ==="
	docker-compose ps
	@echo "\n=== All Related Containers ==="
	docker ps --filter "name=load" --filter "name=Server" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Debug information
debug:
	@echo "=== System Information ==="
	@echo "Docker version:"
	docker --version
	@echo "Docker Compose version:"
	docker-compose --version
	@echo "\n=== Network Information ==="
	docker network ls | grep load-balancer-project || echo "No networks found"
	@echo "\n=== Container Logs ==="
	docker-compose logs --tail=20

# Quick restart
restart: down up