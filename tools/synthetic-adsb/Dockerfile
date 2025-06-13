FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create a startup script that runs both services
COPY <<EOF /app/start.sh
#!/bin/bash
set -e

# Start server.py in the background
echo "Starting ADS-B server..."
python server.py &
SERVER_PID=\$!

# Wait a moment for server to start
sleep 2

# Start bridge.py in the foreground
echo "Starting bridge..."
python bridge.py &
BRIDGE_PID=\$!

# Function to handle shutdown
shutdown() {
    echo "Shutting down..."
    kill \$SERVER_PID \$BRIDGE_PID 2>/dev/null || true
    wait \$SERVER_PID \$BRIDGE_PID 2>/dev/null || true
    exit 0
}

# Set up signal handling
trap shutdown SIGTERM SIGINT

# Wait for both processes
wait \$SERVER_PID \$BRIDGE_PID
EOF

RUN chmod +x /app/start.sh

# Expose ports
# 5001 - ADS-B data server
# 49158-49160 - Radar APIs (rx1, rx2, rx3)
EXPOSE 5001 49158 49159 49160

CMD ["/app/start.sh"]
