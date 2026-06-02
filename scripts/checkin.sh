#!/bin/bash
# Multi-account automatic check-in scheduler wrapper with retry logic
export GLADOS_COOKIES="koa:sess=YOUR_COOKIE_A; koa:sess.sig=YOUR_SIG_A&koa:sess=YOUR_COOKIE_B; koa:sess.sig=YOUR_SIG_B"
export PUSHDEER_SENDKEY="PDBOX1234567890..."
export GLADOS_EXCHANGE_PLAN="plan500"

# Navigate to execution context
cd "$(dirname "$0")"
source venv/bin/activate

MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempting check-in (Try $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    OUTPUT=$(python3 checkin.py 2>&1)
    echo "$OUTPUT"
    
    if echo "$OUTPUT" | grep -qE "Check-in Success|Already Checked In|重复签到|签到成功"; then
        SUCCESS=true
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Check-in unconfirmed. Retrying in 30 seconds..."
        sleep 30
    fi
done

if [ "$SUCCESS" = false ]; then
    echo "ERROR: Automatic check-in failed after $MAX_RETRIES attempts."
    exit 1
fi
exit 0
