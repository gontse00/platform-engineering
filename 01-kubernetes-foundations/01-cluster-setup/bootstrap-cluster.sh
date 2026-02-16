#!/bin/bash

# Configuration for AI-Ready Cluster
CPU_REQ=4
MEM_REQ=8192
K8S_VER="v1.35.0"
PROFILE="minikube"

# Function to check if minikube is running (returns 0 if running, 1 if not)
is_running() {
    minikube status -p "$PROFILE" >/dev/null 2>&1
}

case "$1" in
    start)
        echo "Initializing Kubernetes Platform..."
        if is_running; then
            echo "✅ Cluster is already active. Skipping start."
        else
            echo "⚠️  Cluster is down. Starting with $CPU_REQ CPUs and ${MEM_REQ}MB RAM..."
            minikube start --cpus=$CPU_REQ --memory=$MEM_REQ --driver=docker --kubernetes-version=$K8S_VER
            
            echo "🔍 Performing Health Audit..."
            # Wait for API server to respond
            until kubectl get nodes >/dev/null 2>&1; do
                echo "⏳ Waiting for API Server to wake up..."
                sleep 2
            done
            echo "✅ Cluster is Ready."
        fi
        ;;

    kill)
        echo "💣 Tearing down Kubernetes Platform..."
        if is_running; then
            minikube delete -p "$PROFILE"
            echo "✅ Cluster '$PROFILE' has been removed."
        else
            echo "ℹ️  No active cluster found. Nothing to kill."
        fi
        ;;

    *)
        echo "Usage: $0 {start|kill}"
        exit 1
        ;;
esac