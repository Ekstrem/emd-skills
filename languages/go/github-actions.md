# GitHub Actions CI/CD

## Назначение

Каждый Go-микросервис получает CI/CD пайплайн в `.github/workflows/ci.yml`.
Пайплайн: сборка → тесты → Docker-образы по профилям.

## Шаблон workflow

При генерации подставляй `{Context}` (PascalCase) и `{ctx}` (lowercase).

**ВАЖНО:** Docker-теги ОБЯЗАТЕЛЬНО lowercase. `github.repository_owner` может содержать заглавные буквы — используй шаг `Lowercase owner` для приведения к нижнему регистру.

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.23'

      - name: Build
        run: go build ./...

      - name: Test
        run: go test ./... -v

  docker:
    needs: build-and-test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        profile: [single, cqrs, ceqrs]
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Lowercase owner
        id: lower
        run: echo "owner=$(echo '${{ github.repository_owner }}' | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_OUTPUT"

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ steps.lower.outputs.owner }}/{ctx}-go:${{ matrix.profile }}
          build-args: DEPLOYMENT_PROFILE=${{ matrix.profile }}
```

## Ключевые моменты

### Go модуль

Go-модуль `github.com/Ekstrem/DigiTFactory.Go.Libraries` опубликован на GitHub. При первой сборке в CI:

1. Убедись, что `go.mod` НЕ содержит `replace` директив на локальные пути
2. Убедись, что зависимость указывает на опубликованный тег (например, `v0.1.0`)
3. Если репозиторий приватный, настрой `GOPRIVATE` в CI:
   ```yaml
   env:
     GOPRIVATE: github.com/Ekstrem/*
   ```

### Lowercase Docker tags

**КРИТИЧНО:** Docker-теги не поддерживают заглавные буквы. `github.repository_owner` (например, `Ekstrem`) нужно привести к lowercase:

```yaml
- name: Lowercase owner
  id: lower
  run: echo "owner=$(echo '${{ github.repository_owner }}' | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_OUTPUT"

# Использование:
tags: ghcr.io/${{ steps.lower.outputs.owner }}/{ctx}-go:${{ matrix.profile }}
```

Без этого шага build упадёт с ошибкой: `repository name must be lowercase`.

### Два джоба

| Job | Когда | Что делает |
|-----|-------|-----------|
| `build-and-test` | Каждый push и PR | Build → Test |
| `docker` | Push в main | Matrix build: 3 Docker-образа по профилям |

### Matrix build

CI собирает **3 Docker-образа** — по одному на каждый профиль:

```
ghcr.io/{owner}/{ctx}-go:single  ← DEPLOYMENT_ROLE=All, EventBus=InMemory
ghcr.io/{owner}/{ctx}-go:cqrs    ← разделение Command/Query
ghcr.io/{owner}/{ctx}-go:ceqrs   ← Command/Event/Query + Kafka
```

### Dockerfile

```dockerfile
FROM golang:1.23-alpine AS builder
RUN apk add --no-cache git
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /{ctx}-api ./cmd/{ctx}/

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=builder /{ctx}-api /{ctx}-api
ARG DEPLOYMENT_PROFILE=Single
ENV DEPLOYMENT_ROLE=All
ENV SERVER_PORT=8080
EXPOSE 8080
ENTRYPOINT ["/{ctx}-api"]
```

## Что генерировать

При создании нового микросервиса генерируй:

1. `.github/workflows/ci.yml` — из шаблона выше с подстановкой `{ctx}`
2. `Dockerfile` — из шаблона выше с подстановкой `{ctx}`

### Типичные ошибки в CI

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `replacement directory does not exist` | `replace` директива в go.mod указывает на локальную папку | Удалить `replace`, использовать опубликованный тег |
| `unknown revision v0.X.X` | Тег не опубликован или Go proxy кеширует | Проверить `git ls-remote --tags origin`, подождать или `GONOSUMCHECK` |
| `repository name must be lowercase` | `github.repository_owner` с заглавной | Добавить шаг `Lowercase owner` |
