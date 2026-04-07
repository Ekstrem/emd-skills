# Deployment Profiles — Kotlin/JVM

> 4 профиля деплоймента для Kotlin/JVM микросервиса.

## Профили

| Профиль | Command Store | Event Bus | Read Store |
|---------|-------------|-----------|-----------|
| **Single** | PostgreSQL | InMemory | PostgreSQL (та же БД) |
| **BudgetCqrs** | PostgreSQL | InMemory | PostgreSQL (отдельная БД) |
| **Cqrs** | PostgreSQL | Postgres Outbox | PostgreSQL |
| **Ceqrs** | PostgreSQL | Kafka | PostgreSQL / Redis / ScyllaDB |

## HOCON конфигурация

### application.conf (базовый)

```hocon
ktor {
    deployment { port = 8080, port = ${?PORT} }
    application { modules = [ io.github.ekstrem.chat.api.ApplicationKt.module ] }
}
deployment { role = "All", role = ${?DEPLOYMENT_ROLE}, profile = "Single", profile = ${?DEPLOYMENT_PROFILE} }
command-store { url = "jdbc:postgresql://localhost:5432/chat_command", url = ${?COMMAND_DB_URL} }
event-bus { strategy = "InMemory", strategy = ${?EVENT_BUS_STRATEGY} }
read-store { url = "jdbc:postgresql://localhost:5432/chat_read", url = ${?READ_DB_URL} }
```

## Koin DI по профилю

```kotlin
fun chatModule(config: ApplicationConfig) = module {
    val profile = config.property("deployment.profile").getString()
    when (profile) {
        "Single", "BudgetCqrs" -> single<EventBus> { InMemoryEventBus() }
        "Cqrs" -> single<EventBus> { PostgresOutboxEventBus(get()) }
        "Ceqrs" -> single<EventBus> { KafkaEventBus(config) }
    }
}
```

## Docker

### Dockerfile

```dockerfile
FROM gradle:8.10-jdk17 AS build
WORKDIR /app
COPY . .
RUN gradle :chat-api:shadowJar --no-daemon

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/chat-api/build/libs/*-all.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

## Переменные окружения

| Переменная | По умолчанию |
|-----------|-------------|
| `DEPLOYMENT_PROFILE` | Single |
| `DEPLOYMENT_ROLE` | All |
| `COMMAND_DB_URL` | jdbc:postgresql://localhost:5432/chat_command |
| `READ_DB_URL` | jdbc:postgresql://localhost:5432/chat_read |
| `EVENT_BUS_STRATEGY` | InMemory |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 |
