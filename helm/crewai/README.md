# CrewAI Helm Chart

Enterprise-grade Helm chart for deploying CrewAI to Kubernetes.

## TL;DR

```bash
helm install crewai ./helm/crewai
```

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PersistentVolume provisioner (for data persistence)

## Installing the Chart

```bash
# Install with default values
helm install crewai ./helm/crewai

# Install with custom values
helm install crewai ./helm/crewai -f my-values.yaml

# Install in specific namespace
helm install crewai ./helm/crewai --namespace crewai --create-namespace
```

## Uninstalling the Chart

```bash
helm uninstall crewai
```

## Configuration

The following table lists the configurable parameters and their default values.

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Container image repository | `crewai` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.tag` | Image tag | `1.5.0` |

### Deployment Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `3` |
| `strategy.type` | Deployment strategy | `RollingUpdate` |

### Service Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `LoadBalancer` |
| `service.port` | Service port | `80` |
| `service.metricsPort` | Metrics port | `9090` |

### Resource Limits

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `512Mi` |

### Autoscaling

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `3` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | CPU target | `70` |

### Persistence

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.size` | PVC size | `50Gi` |
| `persistence.storageClass` | Storage class | `""` (default) |

## Examples

### Production Deployment

```yaml
# production-values.yaml
replicaCount: 5

resources:
  limits:
    cpu: 4000m
    memory: 8Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  minReplicas: 5
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60

persistence:
  size: 200Gi
  storageClass: "fast-ssd"

secrets:
  existingSecret: "crewai-production-secrets"
```

```bash
helm install crewai ./helm/crewai -f production-values.yaml
```

### Development Deployment

```yaml
# dev-values.yaml
replicaCount: 1

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: false

env:
  ENVIRONMENT: development
  CREWAI_LOG_LEVEL: DEBUG
```

```bash
helm install crewai ./helm/crewai -f dev-values.yaml
```

### With Ingress

```yaml
# ingress-values.yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: crewai.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: crewai-tls
      hosts:
        - crewai.example.com
```

## Upgrading

```bash
helm upgrade crewai ./helm/crewai -f my-values.yaml
```

## Rollback

```bash
helm rollback crewai
```

## Troubleshooting

### Check deployment status
```bash
kubectl get pods -l app.kubernetes.io/name=crewai
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Check service
```bash
kubectl get svc
kubectl describe svc crewai
```

### Check HPA
```bash
kubectl get hpa
kubectl describe hpa crewai
```

## License

MIT
