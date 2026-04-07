# GitHub Actions CI/CD

## Назначение

Каждый микросервис получает CI/CD пайплайн в `.github/workflows/ci.yml`.
Пайплайн: сборка → unit-тесты → интеграционные тесты → Docker-образы по профилям.

## Шаблон workflow

При генерации подставляй `{Context}` (имя контекста, PascalCase) и `{context}` (lowercase).

```yaml
name: Build and publish {Context} microservice

on:
  push:
    branches: [ dev*, main ]
  pull_request:
    branches: [ main ]
    paths:
      - src/**
      - Dockerfile
      - .github/workflows/**

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup .NET
      uses: actions/setup-dotnet@v4
      with:
        dotnet-version: 8.0.x

    - name: Restore dependencies
      run: dotnet restore src/{Context}.sln

    - name: Build
      run: dotnet build src/{Context}.sln --no-restore --configuration Release

    - name: Unit Tests
      run: dotnet test src/{Context}.Domain.Tests/{Context}.Domain.Tests.csproj --no-build --configuration Release --verbosity normal

    - name: Integration Tests
      run: dotnet test src/{Context}.IntegrationTests/{Context}.IntegrationTests.csproj --no-build --configuration Release --verbosity normal

  docker:
    needs: build-and-test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        profile:
          - { name: Single, tag: single }
          - { name: BudgetCqrs, tag: budget-cqrs }
          - { name: Cqrs, tag: cqrs }
          - { name: Ceqrs, tag: ceqrs }

    steps:
    - uses: actions/checkout@v4

    - name: Log in to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=raw,value=${{ matrix.profile.tag }}
          type=sha,prefix=${{ matrix.profile.tag }}-

    - name: Build and push Docker image (${{ matrix.profile.name }})
      uses: docker/build-push-action@v6
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        build-args: |
          DEPLOYMENT_PROFILE=${{ matrix.profile.name }}

  docker-latest:
    needs: docker
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - uses: actions/checkout@v4

    - name: Log in to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push latest (Single profile)
      uses: docker/build-push-action@v6
      with:
        context: .
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
        build-args: |
          DEPLOYMENT_PROFILE=Single
```

## Ключевые моменты

### NuGet

Пакеты `DigiTFactory.Libraries.*` опубликованы на **nuget.org** — дополнительная аутентификация не требуется. `dotnet restore` работает из коробки.

### Три джоба

| Job | Когда | Что делает |
|-----|-------|-----------|
| `build-and-test` | Каждый push и PR | Restore → Build → Unit Tests → Integration Tests |
| `docker` | Push в main | Matrix build: 4 Docker-образа по профилям |
| `docker-latest` | Push в main (после docker) | Публикует `latest` тег (= Single профиль) |

### Matrix build

CI собирает **4 Docker-образа** — по одному на каждый профиль деплоймента:

```
ghcr.io/{owner}/{context}:single       ← ASPNETCORE_ENVIRONMENT=Single
ghcr.io/{owner}/{context}:budget-cqrs  ← ASPNETCORE_ENVIRONMENT=BudgetCqrs
ghcr.io/{owner}/{context}:cqrs         ← ASPNETCORE_ENVIRONMENT=Cqrs
ghcr.io/{owner}/{context}:ceqrs        ← ASPNETCORE_ENVIRONMENT=Ceqrs
ghcr.io/{owner}/{context}:latest       ← алиас для Single
```

Каждый образ использует один и тот же Dockerfile, но с разным `DEPLOYMENT_PROFILE` build-arg → `ASPNETCORE_ENVIRONMENT`.

### Dockerfile

```dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 8080

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY src/{Context}.Api/{Context}.Api.csproj {Context}.Api/
# ... остальные csproj
RUN dotnet restore {Context}.Api/{Context}.Api.csproj
COPY src/ .
RUN dotnet publish {Context}.Api/{Context}.Api.csproj -c Release -o /app/publish --no-restore

FROM base AS final
ARG DEPLOYMENT_PROFILE=Single
ENV ASPNETCORE_ENVIRONMENT=${DEPLOYMENT_PROFILE}
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "{Context}.Api.dll"]
```

### Что генерировать

При создании нового микросервиса генерируй:

1. `.github/workflows/ci.yml` — из шаблона выше с подстановкой `{Context}`
2. `Dockerfile` — из шаблона выше с подстановкой `{Context}`

CI запускает оба тестовых проекта:
- `{Context}.Domain.Tests` — unit-тесты домена (быстрые, без инфраструктуры)
- `{Context}.IntegrationTests` — сквозные тесты (WebApplicationFactory, профиль Single)
