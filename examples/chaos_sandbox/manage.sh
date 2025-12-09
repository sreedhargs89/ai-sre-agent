#!/bin/bash

ACTION=$1

if [ "$ACTION" == "start" ]; then
    echo "🔥 Igniting Chaos Sandbox..."
    kubectl apply -f 01-frontend.yaml
    kubectl apply -f 02-backend-crash.yaml
    kubectl apply -f 03-worker-oom.yaml
    echo "✅ Chaos deployed. Wait ~30s for failures to appear."
elif [ "$ACTION" == "stop" ]; then
    echo "🧯 Extinguishing Chaos..."
    kubectl delete -f 01-frontend.yaml
    kubectl delete -f 02-backend-crash.yaml
    kubectl delete -f 03-worker-oom.yaml
    echo "✅ Cleanup complete."
else
    echo "Usage: ./manage.sh [start|stop]"
fi
