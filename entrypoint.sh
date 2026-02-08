#!/bin/sh

set -e  # Exit on error

echo "=== Moderation Microservice Startup ==="

# Railway provides DATABASE_URL and database is already running
if [ "$DATABASE_URL" ]; then
    echo "Railway deployment detected (DATABASE_URL is set)"
    echo "Skipping database wait - Railway database is already provisioned"
elif [ "$SQL_HOST" ]; then
    echo "Docker Compose deployment detected"
    echo "Waiting for PostgreSQL at $SQL_HOST:$SQL_PORT..."

    until nc -z -w 1 "$SQL_HOST" "$SQL_PORT" 2>/dev/null; do
      echo "PostgreSQL is unavailable - sleeping"
      sleep 1
    done

    echo "✓ PostgreSQL is up"
fi

# Verify database connection (works for both Railway and Docker)
echo "Verifying database connection..."
python manage.py check --database default || {
    echo "ERROR: Database connection failed"
    echo "Please check your database configuration:"
    echo "  - Railway: Ensure PostgreSQL service is provisioned"
    echo "  - Docker: Ensure 'db' service is running"
    exit 1
}
echo "✓ Database connection verified"

# Check for pending migrations
echo "Checking for pending migrations..."
if python manage.py showmigrations --plan | grep -q "\[ \]"; then
    echo "Pending migrations found. Applying..."

    # Try migration with error handling
    if python manage.py migrate --noinput; then
        echo "✓ Migrations applied successfully"
    else
        echo "ERROR: Migration failed. Attempting fake migration for existing schema..."
        # This handles the case where tables exist but migrations table is corrupted
        python manage.py migrate --fake-initial || {
            echo "CRITICAL: Migration failed completely. Manual intervention required."
            exit 1
        }
        echo "⚠ Migrations faked successfully (schema already exists)"
    fi
else
    echo "✓ No pending migrations"
fi

# Create logs directory if it doesn't exist
mkdir -p /app/logs
chmod 755 /app/logs

echo "=== Startup Complete ==="
echo ""

exec "$@"
