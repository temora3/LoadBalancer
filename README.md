# Distributed Load Balancer with Consistent Hashing

## Overview
This project implements a customizable load balancer using consistent hashing to distribute client requests across multiple server replicas in a Docker environment.

## Architecture
- **Load Balancer**: Routes requests using consistent hashing algorithm
- **Server Replicas**: Simple web servers that handle client requests
- **Docker Network**: Internal network for container communication
- **Health Monitoring**: Automatic failure detection and recovery

## Features
- Consistent hashing with virtual servers
- Automatic server failure detection and replacement
- Dynamic scaling (add/remove servers)
- RESTful API for management
- Comprehensive performance analysis

## Quick Start

### Prerequisites
- Ubuntu 20.04 LTS or above
- Docker 20.10.23+
- Docker Compose
- Python 3.9+ (for testing)

### Installation and Deployment
```bash
# Clone the repository
git clone <your-repo-url>
cd load-balancer-project

# Build and start the system
make up

# Check status
make status

# View logs
make logs

# Run tests
cd tests && python performance_test.py

# Stop the system
make down