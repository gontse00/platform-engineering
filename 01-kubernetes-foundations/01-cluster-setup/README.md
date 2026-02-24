Lab 01: Local Foundation & Control Plane Audit
1. Objective
To establish a stable, local Kubernetes environment using Minikube and perform a "white-box" audit of the Control Plane components. This ensures the infrastructure is ready for high-resource AI workloads.

2. Environment Specifications
Node Type: Single-node Minikube

Driver: Docker

Resources: 4 CPUs, 8GB RAM (Minimum for local AI inference)

Kubernetes Version: v1.33.0

3. Execution Log
I used the following command to ensure the cluster has enough "headroom" for future LLM containers:

minikube start --cpus=4 --memory=8192 --driver=docker --kubernetes-version=v1.33.0


4. Deep-Dive: Idempotent Cluster Management
I transitioned from manual commands to a managed lifecycle script. This follows the Controller Pattern used in Kubernetes itself:

Idempotency: The script checks the current state (is_running) before applying the desired state. This prevents "Resource Locked" errors if the script is run multiple times.

Exit Codes: I used >/dev/null 2>&1 to suppress output and rely on the Exit Status ($?) of minikube status.

Resource Hardening: By hardcoding the CPU/RAM requirements in the script, I ensure that every time I "start," the environment is consistent for my high-demand AI workloads.