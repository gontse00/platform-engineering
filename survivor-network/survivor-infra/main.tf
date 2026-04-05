terraform {
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.11"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.38"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.17"
    }
  }
}

############################
# 1. KIND CLUSTER
############################

resource "kind_cluster" "survivor_net" {
  name           = "survivor-net"
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role  = "control-plane"
      image = "kindest/node:v1.31.0"
    }

    node {
      role  = "worker"
      image = "kindest/node:v1.31.0"
      kubeadm_config_patches = [<<-EOT
kind: JoinConfiguration
nodeRegistration:
  kubeletExtraArgs:
    node-labels: "tier=data"
EOT
      ]
    }

    node {
      role  = "worker"
      image = "kindest/node:v1.31.0"
      kubeadm_config_patches = [<<-EOT
kind: JoinConfiguration
nodeRegistration:
  kubeletExtraArgs:
    node-labels: "tier=compute"
EOT
      ]
    }

    node {
      role  = "worker"
      image = "kindest/node:v1.31.0"
      kubeadm_config_patches = [<<-EOT
kind: JoinConfiguration
nodeRegistration:
  kubeletExtraArgs:
    node-labels: "ingress-ready=true,tier=tools"
EOT
      ]

      extra_port_mappings {
        container_port = 80
        host_port      = 80
      }

      extra_port_mappings {
        container_port = 443
        host_port      = 443
      }
    }
  }
}

# Automatically load your custom MinIO image into Kind after cluster creation
# resource "null_resource" "load_minio_image" {
#   depends_on = [kind_cluster.survivor_net]
#   provisioner "local-exec" {
#     command = "kind load docker-image minio/minio:latest --name ${kind_cluster.survivor_net.name}"
#   }
# }

############################
# 2. PROVIDERS
############################

provider "kubernetes" {
  host                   = kind_cluster.survivor_net.endpoint
  cluster_ca_certificate = kind_cluster.survivor_net.cluster_ca_certificate
  client_certificate     = kind_cluster.survivor_net.client_certificate
  client_key             = kind_cluster.survivor_net.client_key
}

provider "helm" {
  kubernetes {
    host                   = kind_cluster.survivor_net.endpoint
    cluster_ca_certificate = kind_cluster.survivor_net.cluster_ca_certificate
    client_certificate     = kind_cluster.survivor_net.client_certificate
    client_key             = kind_cluster.survivor_net.client_key
  }
}

############################
# 3. NAMESPACES
############################

resource "kubernetes_namespace" "namespaces" {
  for_each = toset(["data", "observability", "argo", "survivor-apps"])
  metadata {
    name = each.key
    labels = {
      managed-by = "terraform"
      env        = "prod-local"
    }
  }
}

############################
# 4. INGRESS NGINX
############################

resource "helm_release" "ingress_nginx" {
  name       = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  namespace  = "kube-system"

  set {
    name  = "controller.service.type"
    value = "NodePort"
  }
  set {
    name  = "controller.hostPort.enabled"
    value = "true"
  }
  set {
    name  = "controller.nodeSelector.ingress-ready"
    value = "true"
    type  = "string"
  }
  set {
    name  = "controller.watchIngressWithoutClass"
    value = "true"
  }
}

############################
# 5. DATA TIER: POSTGRESQL
############################

resource "helm_release" "postgresql" {
  depends_on = [kubernetes_namespace.namespaces]
  name       = "survivor-db"
  namespace  = "data"
  chart      = "./postgresql-18.5.7.tgz"

  values = [
    yamlencode({
      primary = {
        nodeSelector = {
          tier = "data"
        }
        persistence = {
          enabled = false
        }
      }
      auth = {
        postgresPassword = "survivor-db-pw"
        username         = "survivor"
        password         = "survivor-pw"
        database         = "survivor"
      }
    })
  ]
}

############################
# 6. DATA TIER: MINIO
############################

resource "helm_release" "minio" {
  depends_on = [kubernetes_namespace.namespaces]
  name       = "survivor-storage"
  namespace  = "data"
  chart      = "./minio" 

  values = [
    yamlencode({
      image = "minio/minio:latest"
      nodeSelector = {
        tier = "data"
      }
      auth = {
        rootUser     = "survivor-admin"
        rootPassword = "survivor-storage-pw"
      }
      # Critical for Ingress redirection to work
      extraEnvVars = [
        { name = "MINIO_BROWSER_REDIRECT_URL", value = "http://minio.127.0.0.1.nip.io" },
        { name = "MINIO_SERVER_URL", value = "http://survivor-storage.data.svc.cluster.local:9000" }
      ]
    })
  ]
}

############################
# 7. INGRESS
############################

resource "kubernetes_ingress_v1" "minio_ingress" {
  depends_on = [helm_release.ingress_nginx, helm_release.minio]
  metadata {
  name      = "minio-ingress"
  namespace = "data"

  annotations = {
    "nginx.ingress.kubernetes.io/enable-cors"            = "true"
    "nginx.ingress.kubernetes.io/cors-allow-credentials" = "true"
    "nginx.ingress.kubernetes.io/cors-allow-methods"     = "PUT, GET, POST, OPTIONS, DELETE"
    "nginx.ingress.kubernetes.io/cors-allow-origin"      = "http://minio.127.0.0.1.nip.io, http://minio-api.127.0.0.1.nip.io"
    "nginx.ingress.kubernetes.io/proxy-body-size"        = "1024m"
    "nginx.ingress.kubernetes.io/ssl-redirect"           = "false"

    # required
    "nginx.ingress.kubernetes.io/proxy-http-version"     = "1.1"
    "nginx.ingress.kubernetes.io/proxy-read-timeout"     = "600"
    "nginx.ingress.kubernetes.io/proxy-send-timeout"     = "600"
  }
}

  spec {
    ingress_class_name = "nginx"

    rule {
      host = "minio.127.0.0.1.nip.io"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "survivor-storage"
              port { number = 9001 }
            }
          }
        }
      }
    }

    rule {
      host = "minio-api.127.0.0.1.nip.io"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "survivor-storage"
              port { number = 9000 }
            }
          }
        }
      }
    }
  }
}

############################
# 8. OBSERVABILITY
############################

# Prometheus + Grafana + Alertmanager
resource "helm_release" "kube_prometheus_stack" {
  depends_on = [kubernetes_namespace.namespaces, helm_release.ingress_nginx]
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "observability"
  timeout    = 600

  values = [
    yamlencode({
      alertmanager = {
        enabled = false
      }
      prometheusOperator = {
        enabled = false
      }
      prometheus = {
        prometheusSpec = {
          nodeSelector = { tier = "tools" }
          storageSpec  = {}
        }
        ingress = {
          enabled          = true
          ingressClassName = "nginx"
          hosts            = ["prometheus.127.0.0.1.nip.io"]
          paths            = ["/"]
        }
      }
      grafana = {
        nodeSelector  = { tier = "tools" }
        adminPassword = "survivor-grafana-pw"
        ingress = {
          enabled          = true
          ingressClassName = "nginx"
          hosts            = ["grafana.127.0.0.1.nip.io"]
          path             = "/"
        }
        additionalDataSources = [
          {
            name      = "Loki"
            type      = "loki"
            url       = "http://loki.observability.svc.cluster.local:3100"
            access    = "proxy"
            isDefault = false
          },
          {
            name      = "Tempo"
            type      = "tempo"
            url       = "http://tempo.observability.svc.cluster.local:3100"
            access    = "proxy"
            isDefault = false
          }
        ]
      }
      kubeStateMetrics = {
        enabled = false
      }
      nodeExporter = {
        enabled = false
      }
    })
  ]
}

# Loki — log aggregation (SingleBinary mode for local dev)
resource "helm_release" "loki" {
  depends_on = [kubernetes_namespace.namespaces]
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  namespace  = "observability"
  timeout    = 300

  values = [
    yamlencode({
      deploymentMode = "SingleBinary"
      loki = {
        auth_enabled = false
        commonConfig = {
          replication_factor = 1
        }
        storage = {
          type = "filesystem"
        }
        schemaConfig = {
          configs = [{
            from         = "2024-01-01"
            store        = "tsdb"
            object_store = "filesystem"
            schema       = "v13"
            index = {
              prefix = "loki_index_"
              period = "24h"
            }
          }]
        }
      }
      singleBinary = {
        replicas     = 1
        nodeSelector = { tier = "tools" }
      }
      backend      = { replicas = 0 }
      read         = { replicas = 0 }
      write        = { replicas = 0 }
      lokiCanary   = { enabled = false }
      chunksCache  = { enabled = false }
      resultsCache = { enabled = false }
      gateway      = { enabled = false }
      test         = { enabled = false }
    })
  ]
}

# Promtail — ships pod logs to Loki (runs as DaemonSet on all nodes)
resource "helm_release" "promtail" {
  depends_on = [helm_release.loki]
  name       = "promtail"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "promtail"
  namespace  = "observability"

  values = [
    yamlencode({
      nodeSelector = { tier = "tools" }
      config = {
        clients = [{
          url = "http://loki.observability.svc.cluster.local:3100/loki/api/v1/push"
        }]
      }
    })
  ]
}

# Tempo — distributed tracing for agent workflows
resource "helm_release" "tempo" {
  depends_on = [kubernetes_namespace.namespaces]
  name       = "tempo"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "tempo"
  namespace  = "observability"

  values = [
    yamlencode({
      nodeSelector = { tier = "tools" }
      tempo = {
        storage = {
          trace = {
            backend = "local"
            local   = { path = "/var/tempo/traces" }
          }
        }
      }
    })
  ]
}

variable "backend_image_tag" {
  type    = string
  default = "latest"
}

resource "null_resource" "build_backend_image" {
  depends_on = [kind_cluster.survivor_net]

  triggers = {
    dockerfile_sha = filesha256("${path.module}/../dashboard/backend/Dockerfile")
    image_tag      = var.backend_image_tag
  }

  provisioner "local-exec" {
    command = "docker build -t survivor-net/mission-control:${var.backend_image_tag} ${path.module}/../dashboard/backend"
  }
}

resource "null_resource" "load_backend_image" {
  depends_on = [null_resource.build_backend_image]

  triggers = {
    image_tag = var.backend_image_tag
  }

  provisioner "local-exec" {
    command = "kind load docker-image survivor-net/mission-control:${var.backend_image_tag} --name ${kind_cluster.survivor_net.name}"
  }
}

resource "null_resource" "apply_backend_manifests" {
  depends_on = [
    kubernetes_namespace.namespaces,
    helm_release.ingress_nginx,
    helm_release.postgresql,
    helm_release.minio,
    null_resource.load_backend_image
  ]

  triggers = {
    deployment_sha = filesha256("${path.module}/../dashboard/backend/deploy/deployment.yaml")
    ingress_sha    = filesha256("${path.module}/../dashboard/backend/deploy/ingress.yaml")
    image_tag      = var.backend_image_tag
  }

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/../dashboard/backend/deploy/"
  }
}

resource "null_resource" "restart_backend" {
  depends_on = [null_resource.apply_backend_manifests]

  triggers = {
    image_tag = var.backend_image_tag
  }

  provisioner "local-exec" {
    command = "kubectl rollout restart deployment/survivor-mission-control -n survivor-apps"
  }
}

resource "null_resource" "rollout_backend" {
  depends_on = [null_resource.restart_backend]

  triggers = {
    image_tag = var.backend_image_tag
  }

  provisioner "local-exec" {
    command = "kubectl rollout status deployment/survivor-mission-control -n survivor-apps --timeout=180s"
  }
}