# README — шаблон

## Назначение

Каждый микросервис получает полный README.md. Генерируется из артефактов проектирования и реализации.

## Шаблон

```markdown
# {Context}.Go

Событийно-управляемый микросервис {описание} на Go.
Реализует **DDD**, **Event Sourcing** и **CQRS/CEQRS** с библиотекой [DigiTFactory.Go.Libraries](https://github.com/Ekstrem/DigiTFactory.Go.Libraries).

[![CI](https://github.com/{owner}/{Context}.Go/actions/workflows/ci.yml/badge.svg)](https://github.com/{owner}/{Context}.Go/actions/workflows/ci.yml)

---

## Архитектура

{Диаграмма слоёв: API → Application → Domain Services → Domain → Storage}

---

## Домен

**Bounded Context:** {Context} ({classification})
**Агрегат:** {Aggregate} — {описание}

### Операции агрегата

| Команда | Описание |
|---------|----------|
{Из секции 6 Aggregate Canvas}

### Жизненный цикл

{Из секции 3 — диаграмма состояний}

### Инварианты

{Из секции 4}

---

## API

### Команды (Write Side)

| Метод | Эндпоинт | Операция |
|-------|----------|----------|
{Из артефакта 3 — Command API}

### Запросы (Read Side)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
{Из артефакта 4 — Query API}

### Администрирование

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | /api/admin/rebuild-projections | Пересобрать Read Model |

### Формат ответа команд

json
{
  "aggregateId": "...",
  "version": 1,
  "result": "Success",
  "reasons": [],
  "isSuccess": true
}

---

## Профили развёртывания

| Профиль | Процессы | Event Bus | Пропускная способность |
|---------|----------|-----------|----------------------|
| **Single** | 1 (All) | InMemory | Dev / демо |
| **CQRS** | 2 (Command + Query) | PostgreSQL Outbox | Средняя нагрузка |
| **CEQRS** | 3 (Command + Event + Query) | Kafka | Высокая нагрузка |

---

## Конфигурация

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
{Из config.go — все env переменные}

---

## Быстрый старт

### Локально

bash
go build -o {ctx}-api ./cmd/{ctx}
export COMMAND_STORE_CONNECTION="postgres://..."
./{ctx}-api

### Docker Compose

bash
# Single
docker compose -f docker/docker-compose.single.yml up

# CQRS
docker compose -f docker/docker-compose.cqrs.yml up

# CEQRS
docker compose -f docker/docker-compose.ceqrs.yml up

### Kubernetes (одной командой)

bash
kubectl apply -k k8s/overlays/single
kubectl apply -k k8s/overlays/cqrs
kubectl apply -k k8s/overlays/ceqrs

---

## Структура проекта

{Дерево файлов}

---

## Стек технологий

- **Go 1.23**
- **DigiTFactory.Go.Libraries** — DDD/Event Sourcing
- **chi v5** — HTTP-роутер
- **pgx v5** — PostgreSQL
- **PostgreSQL 16** — Event Store и Read Store
- **Apache Kafka** — Event Bus (CEQRS)
- **Docker** & **Kubernetes**

---

## CI/CD

GitHub Actions: build → test → Docker matrix (single, cqrs, ceqrs)

---

## Документация домена

- [Bounded Context Canvas](Docs/Discovery/1-bounded-context-canvas.md)
- [Aggregate Design Canvas](Docs/Discovery/2-aggregate-design-canvas.md)
- [Command API](Docs/Discovery/3-command-api.md)
- [Query API](Docs/Discovery/4-query-api.md)
- [Materialized Views](Docs/Discovery/5-materialized-views.md)
```

## Правила генерации

1. Заполняй из реальных артефактов проекта, не из шаблона
2. Включай все env-переменные из config.go
3. Включай команды деплоя одной строкой (Docker Compose и kubectl)
4. Включай ссылки на Discovery-документы
5. Добавляй badge CI/CD
