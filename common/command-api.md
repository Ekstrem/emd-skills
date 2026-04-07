# Command API — проектирование

> API и события, вызывающие изменения состояния агрегата.
> Вход: секция 6 (Handled Commands) Aggregate Design Canvas.
> Атрибуты Request DTO коррелируют с входными Value Objects команды.

## Маппинг команд канваса на эндпоинты

| Тип команды | HTTP-метод | URI-паттерн |
|------------|-----------|-------------|
| Создание агрегата | `POST` | `/api/{context}` |
| Действие над агрегатом | `POST` | `/api/{context}/{id}/{action}` |

Входящие команды из шины (от других сервисов) не имеют HTTP-эндпоинта — обрабатываются Event Consumer.

## Request DTO

Определяются из входных Value Objects команды (колонка «Входные VO» секции 6 канваса).

**Правила:**
- Плоская структура, НЕ повторяет доменные Value Objects
- camelCase в JSON тегах (`json:"userId"`)
- Enum-ы как строки
- AggregateId для действий берётся из URI (`chi.URLParam(r, "id")`), не из тела
- Actor для авторизованных действий берётся из контекста авторизации

## Response DTO (единый для всех команд)

```go
// internal/api/dto/responses.go
type {Context}OperationResponse struct {
    AggregateID uuid.UUID `json:"aggregateId"`
    Version     int64     `json:"version"`
    Result      string    `json:"result"`     // "Success" | "Exception" | "WithWarnings"
    Reasons     []string  `json:"reasons"`
    IsSuccess   bool      `json:"isSuccess"`
}
```

HTTP-статусы: 200 OK (Success/Warnings), 400 Bad Request (Exception).

## Цепочка корреляции имён

```
Request DTO             → Command struct           → метод агрегата              → доменное событие
SubscriberRequest-      → SubscriberRequest-       → aggregate.Subscriber-       → ChatSession-
  QuestionRequest         QuestionCommand            RequestQuestion(model,cmd)    Created
```

## Версионирование

В Go используется prefix `/api/{context}`. При breaking change — `/api/v2/{context}`.

## Шаблон артефакта

```markdown
# Command API: {Context}

## HTTP-эндпоинты

| # | Метод | URI | Команда агрегата | Request DTO | Состояние |
|---|-------|-----|-----------------|-------------|-----------|
| 1 | POST | /api/{ctx} | {CreateCommand} | {Create}Request | New |
| 2 | POST | /api/{ctx}/{id}/{act} | {ActionCommand} | {Action}Request | {State} |

## Входящие события из шины

| # | Событие | Команда агрегата | Источник |
|---|---------|-----------------|---------|

## Request DTO

### {Create}Request
{ /* поля из входных VO */ }

## Response DTO
{Context}OperationResponse (единый)
```

## Как заполнять через диалог

Для каждой Handled Command из секции 6 канваса:
1. «Эта команда создаёт новый агрегат или действует над существующим?»
2. «Какие данные нужны на входе? Из каких Value Objects?»
3. «Кто вызывает эту команду — UI, другой сервис, триггер?»
4. «Нужна ли авторизация? Откуда берётся Actor?»
