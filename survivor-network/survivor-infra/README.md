
---

# 🛡️ Survivor Network: GenAI Infrastructure

This directory contains the **Infrastructure as Code (IaC)** required to bootstrap a production-ready, local Kubernetes environment for the Survivor Network GenAI platform.

## 🏗️ Architecture Overview

Unlike a standard local development setup, this platform uses a **Cellular Multi-Node Topology** running on [Kind](https://kind.sigs.k8s.io/) (Kubernetes in Docker). This mimics a real-world data center by separating duties across different virtual nodes.

### 1. Cluster Topology
The cluster consists of **four nodes** to ensure workload isolation and high availability testing:

* **Control Plane (The Brain):** Manages cluster state, API server, and scheduling.
* **Worker 1 (`tier=data`):** Dedicated to stateful workloads. This is where **PostgreSQL (pgvector)** and **Kafka** live to ensure they don't fight for resources with compute jobs.
* **Worker 2 (`tier=compute`):** The "Muscle." Dedicated to **AI Agent Microservices** and **Spark Streaming** jobs.
* **Worker 3 (`tier=tools`):** The "Gateway." Hosts the **NGINX Ingress Controller** and management tools like **Argo Workflows**.



### 2. Networking & Ingress (The "Front Door")
To bridge the gap between your MacBook and the private Kubernetes network, we use a specialized Ingress configuration:
* **Host Port Mapping:** Ports **80** and **443** on your Mac are mapped directly to the Ingress Controller on the `tools` worker node.
* **Traffic Flow:** `Mac Browser -> Localhost:80 -> NGINX Ingress Pod -> Internal Service`.



---

## 📂 Logical Segmentation (Namespaces)

The environment is partitioned into functional "rooms" to enforce security and resource governance:

| Namespace | Responsibility | Resource Quota |
| :--- | :--- | :--- |
| `data` | Persistent Storage & Events (Postgres, Kafka) | **4 CPU / 8Gi RAM** |
| `survivor-apps` | AI Logic, Agents, and Feature Stores | Unbounded (Development) |
| `argo` | Workflow Orchestration (CI/CD for AI) | Unbounded |
| `observability` | Monitoring (Prometheus, Grafana, Loki) | Unbounded |

---

## 🚀 Getting Started

### Prerequisites
* **Hardware:** Apple Silicon (M1/M2/M3) with 16GB+ RAM recommended.
* **Docker:** Docker Desktop or OrbStack.
* **Tools:** `terraform`, `kind`, `kubectl`, `helm`.

### Initialization
1.  **Initialize Providers:**
    ```bash
    terraform init
    ```
2.  **Deploy Infrastructure:**
    ```bash
    terraform apply -auto-approve
    ```

### Post-Deployment Health Check
```bash
# Verify Nodes and Tiers
kubectl get nodes --show-labels

# Verify Ingress is listening
curl -I http://localhost
```

---

## 🛠️ Maintenance & Troubleshooting

### Provider Deadlocks
If you change the `kind_config` (cluster topology), Terraform may fail to refresh the state of the `helm` or `kubernetes` resources because the API server is unreachable during the swap. 
**Solution:**
1.  `terraform state rm helm_release.ingress_nginx`
2.  `terraform state rm kubernetes_namespace.namespaces`
3.  `kind delete cluster --name survivor-net`
4.  `terraform apply -auto-approve`

### Resource Governance
The `data` namespace is protected by a `ResourceQuota`. If a database pod fails to start with "Insufficient memory," you must increase the quota in `main.tf`.

---