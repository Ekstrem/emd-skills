# Bounded Context Canvas — шаблон и инструкция

## Назначение

Bounded Context Canvas — стратегический артефакт. Один файл на контекст.
Описывает ЧТО делает контекст, не КАК он устроен внутри.
Заполняется до написания кода.

## Шаблон канваса

```markdown
# Bounded Context Canvas: {Context}

## 1. Имя
{Context} — название ограниченного контекста.

## 2. Назначение
Одно предложение: зачем этот контекст существует.

## 3. Стратегическая классификация
- [ ] Core Domain (конкурентное преимущество)
- [ ] Supporting (поддержка core)
- [ ] Generic (типовой функционал)

## 4. Роль домена
- [ ] Execution (исполняет бизнес-операции)
- [ ] Gateway (интеграция с внешними системами)
- [ ] Analysis (аналитика, отчёты)

## 5. Входящая коммуникация (Inbound)
| Кто вызывает | Что вызывает | Формат |
|-------------|-------------|--------|
| UI / другой сервис | Команда | HTTP / Message |

## 6. Исходящая коммуникация (Outbound)
| Кому отправляет | Что отправляет | Формат |
|----------------|---------------|--------|
| Другой сервис | Доменное событие | Event Bus |

## 7. Ubiquitous Language
Ключевые термины домена:
- **Термин** — определение

## 8. Бизнес-решения (Business Decisions)
Какие бизнес-правила контекст обеспечивает.

## 9. Предположения (Assumptions)
Что считаем истинным, но не доказано.

## 10. Зависимости / интеграции
| Контекст | Тип интеграции |
|----------|----------------|
| {OtherContext} | SharedKernel / Partners / ClientSuppliers / Conformist / AntiCorruptionLayer / OpenHostService / PublishedLanguage / SeparateWays |
```

## Как заполнять через диалог

Задавай вопросы в таком порядке:

1. «Как называется ваш контекст? Какую бизнес-задачу он решает?» → секции 1-2
2. «Это ядро бизнеса, поддерживающий или типовой функционал?» → секция 3
3. «Кто будет вызывать этот сервис? Через HTTP или через сообщения?» → секция 5
4. «Какие события он порождает? Кому они нужны?» → секция 6
5. «Назовите 5-7 ключевых терминов предметной области» → секция 7
6. «Какие бизнес-правила обязательно должны соблюдаться?» → секция 8
7. «С какими другими контекстами он взаимодействует?» → секция 10

## Маппинг на Go-код

| Секция канваса | Что генерируется |
|---------------|-----------------|
| Имя | `var {Context}BoundedContext = definition.BoundedContextDescription{ContextName: "{Context}", MicroserviceVersion: 1}` |
| Inbound | chi-роуты в `internal/api/router.go`, Command structs в `internal/application/commands/` |
| Outbound | `events.DomainEvent`, публикация через `events.EventBus` |
| Ubiquitous Language | Имена Value Objects structs, методов агрегата, typed constants |
| Business Decisions | `invariants.BusinessOperationSpecification` в `internal/domain/specifications/` |
| Зависимости | `definition.InteractionOfBoundedContexts`, AntiCorruptionLayer при необходимости |
