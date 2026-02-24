Design Rationale: Multi-Node Lab for Kubernetes Mastery
Setting up a local cluster with a dedicated 1 Control Plane / 2 Worker topology is a strategic choice. This configuration moves beyond simple application deployment and simulates the operational complexities of a production environment.

1. Verification of Scheduling & Topology
In a single-node setup (like standard Minikube), the Scheduler's job is trivial. By providing multiple worker nodes, we can validate:

Pod Anti-Affinity: Ensuring replicas are distributed across different physical (or virtual) hosts to prevent a single point of failure.

Taints and Tolerations: Simulating "Specialized Infrastructure" by tainting one node and observing how the Control Plane manages pod placement.

Node Affinity: Forcing workloads onto specific nodes to simulate data locality or hardware-specific requirements.

2. Deep Network Observability (CNI)
A multi-node cluster is essential for mastering Container Networking Interface (CNI) concepts. It allows us to distinguish between two distinct traffic patterns:

Intra-Node (Pod-to-Pod): Traffic staying within the same Linux bridge and network namespace.

Inter-Node (East-West Traffic): Traffic that must leave the node, traverse the "physical" host network (the Docker bridge in this case), and be routed to a destination on a different subnet.

Service Load Balancing: Observing how kube-proxy synchronizes iptables rules across multiple nodes to ensure a ClusterIP reaches a healthy pod regardless of its location.

3. Control Plane vs. Data Plane Isolation
By separating roles, we mirror the security and operational boundaries of a production cluster.

Control Plane: Houses the "Brain" (etcd, API Server). Keeping this isolated allows us to practice cluster upgrades and certificate rotations without confusing host-level issues with application-level issues.

Workers (Data Plane): This is the "Brawn" where workloads live. We use multiple workers to practice Node Draining and Cordoning, simulating real-world maintenance windows where we must migrate traffic without downtime.

4. Portability and "GitOps" Readiness
Storing the cluster-config.yaml alongside the drills ensures that the lab is reproducible.

Immutable Infrastructure: If the cluster state becomes corrupted during a "Hard Drill" (e.g., breaking the API server), we can delete and recreate the entire environment in seconds.

FNB Context: This mirrors the way enterprise environments (like OpenShift) are provisioned—via declarative configuration files rather than manual UI clicks.