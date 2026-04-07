# Kubernetes — Kustomize-манифесты

## Назначение

Каждый профиль деплоймента получает Kustomize overlay. Деплой одной командой:

```bash
kubectl apply -k k8s/overlays/{profile}
```

## Структура директорий

```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── service-account.yaml
│   ├── secret.yaml
│   └── kustomization.yaml
├── infrastructure/
│   ├── postgres.yaml
│   └── kafka.yaml
└── overlays/
    ├── single/
    │   ├── kustomization.yaml
    │   ├── configmap.yaml
    │   ├── deployment.yaml
    │   └── service.yaml
    ├── cqrs/
    │   ├── kustomization.yaml
    │   ├── configmap.yaml
    │   ├── deployment-command.yaml
    │   ├── deployment-query.yaml
    │   └── services.yaml
    └── ceqrs/
        ├── kustomization.yaml
        ├── configmap.yaml
        ├── deployment-command.yaml
        ├── deployment-event.yaml
        ├── deployment-query.yaml
        └── services.yaml
```

## Base

### namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: {ctx}
  labels:
    app.kubernetes.io/part-of: {ctx}-go
```

### secret.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {ctx}-secrets
  namespace: {ctx}
type: Opaque
stringData:
  COMMAND_STORE_CONNECTION: "postgres://postgres:postgres@postgres:5432/{ctx}?sslmode=disable"
  READ_STORE_CONNECTION: "postgres://postgres:postgres@postgres:5432/{ctx}?sslmode=disable"
```

### kustomization.yaml
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - service-account.yaml
  - secret.yaml
```

## Infrastructure

### postgres.yaml
- PersistentVolumeClaim (1Gi)
- Deployment (postgres:16-alpine, 1 replica)
- Service (ClusterIP, port 5432)

### kafka.yaml (только для CEQRS)
- Zookeeper Deployment + Service
- Kafka Deployment + Service

## Overlays

### Single

```yaml
# kustomization.yaml
resources:
  - ../../base
  - ../../infrastructure/postgres.yaml
  - configmap.yaml
  - deployment.yaml
  - service.yaml

# configmap.yaml
data:
  DEPLOYMENT_ROLE: "All"
  EVENT_BUS_STRATEGY: "InMemory"
  SERVER_PORT: "8080"

# deployment.yaml
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: {ctx}-app
          image: ghcr.io/{owner}/{ctx}-go:single
          ports: [{containerPort: 8080}]
          envFrom:
            - configMapRef: {name: {ctx}-config}
            - secretRef: {name: {ctx}-secrets}
          resources:
            requests: {cpu: 50m, memory: 64Mi}
            limits: {cpu: 200m, memory: 128Mi}
          livenessProbe:
            httpGet: {path: /health, port: 8080}
            initialDelaySeconds: 5
          readinessProbe:
            httpGet: {path: /health, port: 8080}
            initialDelaySeconds: 3
```

### CQRS

Два Deployment:
- `{ctx}-command` (DEPLOYMENT_ROLE=Command, port 8080)
- `{ctx}-query` (DEPLOYMENT_ROLE=Query, port 8080 → service port 8081)

Два Service:
- `{ctx}-command` (port 8080)
- `{ctx}-query` (port 8081)

ConfigMap: EVENT_BUS_STRATEGY=Postgres

### CEQRS

Три Deployment:
- `{ctx}-command` (DEPLOYMENT_ROLE=Command)
- `{ctx}-event` (DEPLOYMENT_ROLE=Event) — без Service (внутренний процессор)
- `{ctx}-query` (DEPLOYMENT_ROLE=Query)

Infrastructure: postgres.yaml + kafka.yaml

ConfigMap: EVENT_BUS_STRATEGY=Kafka, Kafka bootstrap servers

## Ресурсы по профилям

| Профиль | CPU requests | CPU limits | Memory requests | Memory limits |
|---------|-------------|-----------|----------------|--------------|
| Single | 50m | 200m | 64Mi | 128Mi |
| CQRS | 50m | 200m | 64Mi | 128Mi |
| CEQRS | 100m | 500m | 128Mi | 256Mi |

## Health Probes

Все deployments должны иметь:
- **Liveness:** `GET /health` (initialDelay: 5s, period: 15s)
- **Readiness:** `GET /health` (initialDelay: 3s, period: 5s)

Если `/health` эндпоинт не реализован — добавь в router:
```go
r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ok"}`))
})
```
