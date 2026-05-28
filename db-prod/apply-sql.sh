#!/bin/bash
# Wrapper to run apply_sql.py with explicit connection parameters.

cd "$(dirname "$0")/.."


if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

read -r -p "MySQL host: " MYSQL_HOST_INPUT
read -r -p "MySQL port [3306]: " MYSQL_PORT_INPUT
read -r -p "MySQL user: " MYSQL_USER_INPUT
read -r -s -p "MySQL password: " MYSQL_PASSWORD_INPUT
echo
read -r -p "Target database: " MYSQL_DATABASE_INPUT

MYSQL_PORT_INPUT=${MYSQL_PORT_INPUT:-3306}

if [ -z "$MYSQL_HOST_INPUT" ] || [ -z "$MYSQL_USER_INPUT" ] || [ -z "$MYSQL_DATABASE_INPUT" ]; then
    echo "❌ Host、User、Target database 都必须手动输入。"
    exit 1
fi

echo "---------------------------------------------------"
echo "请确认本次 SQL 执行目标："
echo "  Host     : $MYSQL_HOST_INPUT"
echo "  Port     : $MYSQL_PORT_INPUT"
echo "  User     : $MYSQL_USER_INPUT"
echo "  Database : $MYSQL_DATABASE_INPUT"
echo "  Password : ******"
if [ $# -eq 0 ]; then
    echo "  SQL files: db-prod/V*.sql"
else
    echo "  SQL file : $*"
fi
read -r -p "确认无误请输入 YES 继续执行：" CONFIRM_INPUT
CONFIRM_UPPER=$(echo "$CONFIRM_INPUT" | tr '[:lower:]' '[:upper:]')
if [ "$CONFIRM_UPPER" != "YES" ]; then
    echo "❌ 已取消，未执行 SQL。"
    exit 1
fi

COMMON_ARGS=(
    --host "$MYSQL_HOST_INPUT"
    --port "$MYSQL_PORT_INPUT"
    --user "$MYSQL_USER_INPUT"
    --password "$MYSQL_PASSWORD_INPUT"
    --database "$MYSQL_DATABASE_INPUT"
    --yes
)

if [ $# -eq 0 ]; then
    echo "No arguments provided. Running all SQL files from db-prod/..."
    DB_DIR="db-prod"
    
    if [ ! -d "$DB_DIR" ]; then
        echo "❌ Directory $DB_DIR not found!"
        exit 1
    fi

    # Sort files by version (V1, V2, ... V10)
    FILES=$(ls "$DB_DIR"/V*.sql 2>/dev/null | sort -V)
    
    if [ -z "$FILES" ]; then
        echo "❌ No SQL files found in $DB_DIR/"
        exit 1
    fi
    
    for f in $FILES; do
        echo "---------------------------------------------------"
        echo "🚀 Applying $f..."
        python3 db-prod/apply_sql.py "$f" "${COMMON_ARGS[@]}"
        if [ $? -ne 0 ]; then
             echo "❌ Failed to apply $f"
             exit 1
        fi
    done
    echo "---------------------------------------------------"
    echo "✅ All SQL files applied successfully."
else
    python3 db-prod/apply_sql.py "$@" "${COMMON_ARGS[@]}"
fi
