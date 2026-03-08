#!/bin/bash
set -e

# ==============================================================================
# AI Smart Investment Advisor - Remote Deployment Script
# Usage: ./remote_deploy.sh <user@host> [ssh_key_path]
# ==============================================================================

REMOTE_TARGET=$1
SSH_KEY_PATH=$2

if [ -z "$REMOTE_TARGET" ]; then
    echo "Usage: $0 <user@host> [ssh_key_path]"
    echo "Example: $0 root@1.2.3.4 ~/.ssh/id_rsa"
    exit 1
fi

SSH_OPTS=""
if [ ! -z "$SSH_KEY_PATH" ]; then
    SSH_OPTS="-i $SSH_KEY_PATH"
fi

echo "🚀 Starting remote deployment to $REMOTE_TARGET..."

# 1. Sync files to remote server
# Exclude heavy or sensitive local directories
echo "📦 Synchronizing files..."
rsync -avz --progress -e "ssh $SSH_OPTS -o StrictHostKeyChecking=no" \
    --exclude '.git/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude '.venv/' \
    --exclude '.next/' \
    --exclude 'ai_advisor.db*' \
    --exclude 'app.log' \
    ./ "$REMOTE_TARGET:~/ai-stock-advisor/"

# 2. Remote command execution
echo "🏗️  Building and starting containers on remote..."
ssh $SSH_OPTS "$REMOTE_TARGET" << 'EOF'
    cd ~/ai-stock-advisor
    
    # Prefer 'docker compose' (v2 plugin) over 'docker-compose' (v1)
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null && [ -x "$(command -v docker-compose)" ]; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        echo "❌ Error: Neither docker compose nor an executable docker-compose found on remote server."
        exit 1
    fi

    echo "Using: $DOCKER_COMPOSE_CMD"
    
    # Stop old services
    $DOCKER_COMPOSE_CMD down
    
    # Build and start
    if ! $DOCKER_COMPOSE_CMD up -d --build; then
        echo "❌ Deployment failed on remote!"
        exit 1
    fi
    
    echo "⏳ Waiting for services to stabilize..."
    sleep 10
    
    # Run migrations (PostgreSQL mode assumes alembic is configured)
    echo "🔄 Running database migrations..."
    if $DOCKER_COMPOSE_CMD ps | grep -q "backend"; then
        $DOCKER_COMPOSE_CMD exec -T backend alembic upgrade head || echo "⚠️ Migration warning: No migrations executed or failed."
    fi
    
    echo "🧹 Cleaning up old images..."
    docker image prune -f
EOF

echo "✅ Remote deployment to $REMOTE_TARGET finished!"
echo "Backend: http://${REMOTE_TARGET#*@}:8000"
echo "Frontend: http://${REMOTE_TARGET#*@}:3000"
