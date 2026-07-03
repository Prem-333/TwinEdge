#!/bin/bash
# Helper script to manage local development containers (Mosquitto & InfluxDB)
# since system docker-compose is unavailable.

ACTION=$1

if [ "$ACTION" == "start" ]; then
    echo "Starting infrastructure containers..."
    
    # 1. Start Mosquitto
    docker rm -f aerotwin_mosquitto 2>/dev/null || true
    docker run -d \
        --name aerotwin_mosquitto \
        -p 1883:1883 \
        -v /home/saran/project/TwinEdge/backend/config/mosquitto.conf:/mosquitto/config/mosquitto.conf \
        eclipse-mosquitto:2.0.18
        
    # 2. Start InfluxDB
    docker rm -f aerotwin_influxdb 2>/dev/null || true
    docker run -d \
        --name aerotwin_influxdb \
        -p 8086:8086 \
        -e DOCKER_INFLUXDB_INIT_MODE=setup \
        -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
        -e DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword \
        -e DOCKER_INFLUXDB_INIT_ORG=aerotwin \
        -e DOCKER_INFLUXDB_INIT_BUCKET=telemetry \
        -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=my-super-secret-admin-token-12345 \
        influxdb:2.7.6
        
    echo "Mosquitto and InfluxDB started successfully."
    docker ps

elif [ "$ACTION" == "stop" ]; then
    echo "Stopping infrastructure containers..."
    docker stop aerotwin_mosquitto aerotwin_influxdb 2>/dev/null || true
    docker rm aerotwin_mosquitto aerotwin_influxdb 2>/dev/null || true
    echo "Infrastructure containers stopped and removed."

elif [ "$ACTION" == "status" ]; then
    docker ps -a --filter name=aerotwin_

else
    echo "Usage: $0 {start|stop|status}"
    exit 1
fi
