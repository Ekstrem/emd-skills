# Implementation Guide — Kotlin/JVM

> Паттерны кода, зависимости и структура проекта для микросервиса на Kotlin/JVM
> с DigiTFactory.Kotlin.Libraries (io.github.ekstrem).

## Пакеты библиотек

| Maven-артефакт | Описание |
|---------------|----------|
| `io.github.ekstrem:seedworks` | Базовые абстракции DDD: BoundedContext, BaseAnemicModel, AggregateResult, BusinessOperationData, ComplexKey, ValueObject, спецификации |
| `io.github.ekstrem:eventbus-inmemory` | In-memory EventBus (Single / BudgetCqrs) |
| `io.github.ekstrem:eventbus-kafka` | Kafka EventBus (Ceqrs) |
| `io.github.ekstrem:eventbus-postgres` | Postgres-outbox EventBus (Cqrs) |
| `io.github.ekstrem:commandrepository-postgres` | Event Store на PostgreSQL |
| `io.github.ekstrem:readrepository-postgres` | Read Store на PostgreSQL |

## Граф зависимостей модулей

```
chat-api
  +-- chat-application
  |     +-- chat-domain
  |     |     +-- seedworks
  |     +-- chat-domain-services
  |           +-- chat-domain
  +-- chat-storage
  |     +-- chat-domain
  |     +-- commandrepository-postgres
  |     +-- readrepository-postgres
  +-- ktor-server-netty
  +-- koin-ktor
```

## libs.versions.toml (шаблон)

```toml
[versions]
kotlin = "2.0.21"
ktor = "3.0.3"
koin = "4.0.0"
exposed = "0.56.0"
coroutines = "1.9.0"
serialization = "1.7.3"
slf4j = "2.0.16"
logback = "1.5.12"
postgresql = "42.7.4"
seedworks = "0.5.10"
junit = "5.11.3"

[libraries]
ktor-server-core = { module = "io.ktor:ktor-server-core", version.ref = "ktor" }
ktor-server-netty = { module = "io.ktor:ktor-server-netty", version.ref = "ktor" }
ktor-server-content-negotiation = { module = "io.ktor:ktor-server-content-negotiation", version.ref = "ktor" }
ktor-serialization-json = { module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }
ktor-server-status-pages = { module = "io.ktor:ktor-server-status-pages", version.ref = "ktor" }
koin-core = { module = "io.insert-koin:koin-core", version.ref = "koin" }
koin-ktor = { module = "io.insert-koin:koin-ktor", version.ref = "koin" }
exposed-core = { module = "org.jetbrains.exposed:exposed-core", version.ref = "exposed" }
exposed-jdbc = { module = "org.jetbrains.exposed:exposed-jdbc", version.ref = "exposed" }
exposed-java-time = { module = "org.jetbrains.exposed:exposed-java-time", version.ref = "exposed" }
postgresql = { module = "org.postgresql:postgresql", version.ref = "postgresql" }
coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "coroutines" }
serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "serialization" }
logback-classic = { module = "ch.qos.logback:logback-classic", version.ref = "logback" }
seedworks = { module = "io.github.ekstrem:seedworks", version.ref = "seedworks" }
eventbus-inmemory = { module = "io.github.ekstrem:eventbus-inmemory", version.ref = "seedworks" }
eventbus-kafka = { module = "io.github.ekstrem:eventbus-kafka", version.ref = "seedworks" }
eventbus-postgres = { module = "io.github.ekstrem:eventbus-postgres", version.ref = "seedworks" }
commandrepository-postgres = { module = "io.github.ekstrem:commandrepository-postgres", version.ref = "seedworks" }
readrepository-postgres = { module = "io.github.ekstrem:readrepository-postgres", version.ref = "seedworks" }
junit-jupiter = { module = "org.junit.jupiter:junit-jupiter", version.ref = "junit" }
kotlin-test = { module = "org.jetbrains.kotlin:kotlin-test", version.ref = "kotlin" }

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
ktor = { id = "io.ktor.plugin", version.ref = "ktor" }
```

## Паттерны кода

### 1. BoundedContext маркер

```kotlin
package io.github.ekstrem.chat.domain
import io.github.ekstrem.seedworks.definition.BoundedContext
interface IChat : BoundedContext
```

### 2. Enums

```kotlin
enum class UserType { Client, Bot, Operator }
enum class MessageType { Text, Voice, Video }
enum class Platform { Linux, Windows, Android }
enum class ChatApplication { Application, Site, IncomingCall }
```

### 3. Value Objects

```kotlin
import io.github.ekstrem.seedworks.tacticalpatterns.ValueObject

data class ChatRoot private constructor(
    val userId: UUID, val sessionId: Int
) : ValueObject {
    companion object {
        fun createInstance(userId: UUID, sessionId: Int) = ChatRoot(userId, sessionId)
    }
}

data class ChatActor private constructor(
    val login: String, val type: UserType
) : ValueObject {
    companion object {
        fun createInstance(login: String, type: UserType) = ChatActor(login, type)
    }
}

data class ChatMessage private constructor(
    val type: MessageType, val text: String,
    val platform: Platform, val application: ChatApplication, val contentId: UUID
) : ValueObject {
    companion object {
        fun createInstance(type: MessageType, text: String,
            platform: Platform, application: ChatApplication, contentId: UUID
        ) = ChatMessage(type, text, platform, application, contentId)
    }
}
```

Паттерн: private constructor + companion object factory createInstance().

### 4. AnemicModel

```kotlin
import io.github.ekstrem.seedworks.characteristics.ComplexKey
import io.github.ekstrem.seedworks.characteristics.ComplexKeyMarker
import io.github.ekstrem.seedworks.tacticalpatterns.BaseAnemicModel

open class ChatAnemicModel protected constructor(
    key: ComplexKeyMarker,
    override val root: IChatRoot?,
    override val actor: IChatActor?,
    override val feedback: IChatFeedback?,
    override val messages: List<IChatMessage>
) : BaseAnemicModel<IChat>(key), IChatAnemicModel {

    private var _commandName: String = ""
    private var _subjectName: String = ""
    override val commandName: String get() = _commandName
    override val subjectName: String get() = _subjectName

    companion object {
        fun create(id: UUID, version: Long, correlationToken: UUID,
            commandName: String, subjectName: String,
            root: IChatRoot?, actor: IChatActor?,
            feedback: IChatFeedback?, messages: List<IChatMessage>
        ): IChatAnemicModel {
            val key = ComplexKey.create(id, version, correlationToken)
            return ChatAnemicModel(key, root, actor, feedback, messages).also {
                it._commandName = commandName; it._subjectName = subjectName
            }
        }
    }
}
```

**КРИТИЧНО**: ComplexKey.create() — конструктор приватный!

### 5. DefaultAnemicModel (null-object)

```kotlin
class DefaultAnemicModel private constructor(id: UUID) : ChatAnemicModel(
    ComplexKey.create(id, 0L, UUID(0, 0)),
    root = null, actor = null, feedback = null, messages = emptyList()
) {
    companion object { fun create(id: UUID): IChatAnemicModel = DefaultAnemicModel(id) }
}
```

### 6. Aggregate — три паттерна операций

```kotlin
import io.github.ekstrem.seedworks.invariants.BusinessOperationData
import io.github.ekstrem.seedworks.monads.pipeTo
import io.github.ekstrem.seedworks.result.validateCommand

class ChatAggregate private constructor(private val anemicModel: IChatAnemicModel) : IChatAggregate {
    companion object { fun create(anemicModel: IChatAnemicModel) = ChatAggregate(anemicModel) }

    // Паттерн 1: Создание — validateCommand
    override fun subscriberRequestQuestion(model: IChatAnemicModel) =
        BusinessOperationData.commit(anemicModel, model)
            .validateCommand(IsNewSubscriberRequestValidator())

    // Паттерн 2: Действие без валидации — pipeTo
    override fun botRepliedToUser(model: IChatAnemicModel, command: CommandToAggregateMarker) =
        ChatAnemicModel.create(anemicModel.id, command,
            anemicModel.root, anemicModel.actor, anemicModel.feedback,
            anemicModel.messages + model.messages
        ).pipeTo { am -> ChatResult(anemicModel, am, DomainOperationResultEnum.SUCCESS, null) }

    // Паттерн 3: Действие с валидацией — pipeTo + validateCommand
    override fun operatorDequeueRequest(model: IChatAnemicModel, command: CommandToAggregateMarker) =
        ChatAnemicModel.create(anemicModel.id, command,
            anemicModel.root, model.actor, anemicModel.feedback,
            anemicModel.messages + model.messages
        ).pipeTo { am ->
            BusinessOperationData.commit(anemicModel, am)
                .validateCommand(IsNotAlreadyDequeuedValidator(), IsSessionActiveValidator())
        }
}
```

### 7. Спецификации

```kotlin
import io.github.ekstrem.seedworks.invariants.BusinessOperationAssertionDefault

class IsNewSubscriberRequestValidator :
    BusinessOperationAssertionDefault<IChat, IChatAnemicModel> {
    override fun isSatisfiedBy(obj: BusinessOperationData<IChat, IChatAnemicModel>) =
        obj.aggregate is DefaultAnemicModel
    override val reason = "Операция применима только для новых сущностей."
    override val domainResult = DomainOperationResultEnum.EXCEPTION
}
```

**КРИТИЧНО**: BusinessOperationAssertionDefault, НЕ BusinessOperationSpecificationDefault!

### 8. Domain Services

```kotlin
// Observer
interface DomainEventObserver<TBC : BoundedContext, TModel : AnemicModelMarker<TBC>> {
    fun onNext(result: AggregateResult<TBC, TModel>)
    fun onError(error: Exception) {}
}

// AggregateProvider
class AggregateProvider(
    private val repository: IRepository,
    private val observers: List<DomainEventObserver<IChat, IChatAnemicModel>> = emptyList()
) : IChatAggregateProvider {
    override suspend fun getAggregate(id: UUID): IChatAggregate {
        val model = repository.getById(id).firstOrNull() ?: DefaultAnemicModel.create(id)
        return NotifyingAggregate(ChatAggregate.create(model), observers)
    }
}

// NotifyingAggregate — proxy через by delegate
private class NotifyingAggregate(
    private val delegate: IChatAggregate,
    private val observers: List<DomainEventObserver<IChat, IChatAnemicModel>>
) : IChatAggregate by delegate {
    private fun notify(result: AggregateResult<IChat, IChatAnemicModel>) = result.also {
        observers.forEach { obs -> try { obs.onNext(it) } catch (e: Exception) { obs.onError(e) } }
    }
    override fun subscriberRequestQuestion(model: IChatAnemicModel) =
        notify(delegate.subscriberRequestQuestion(model))
}
```

### 9. Command/Query Handlers

```kotlin
interface CommandHandler<TCommand, TResult> { suspend fun handle(command: TCommand): TResult }
interface QueryHandler<TQuery, TResult> { suspend fun handle(query: TQuery): TResult }
```

### 10. Ktor API + Koin DI

```kotlin
fun main() {
    embeddedServer(Netty, port = 8080) {
        install(ContentNegotiation) { json() }
        install(Koin) { modules(chatModule()) }
        chatRoutes()
    }.start(wait = true)
}

fun chatModule() = module {
    single<IRepository> { Repository(get()) }
    single<BusAdapter> { BusAdapter(get()) }
    single<IChatAggregateProvider> { AggregateProvider(get(), listOf(get<BusAdapter>())) }
}
```

### 11. Unit Tests (JUnit 5)

```kotlin
class AggregateTest {
    @Test fun `new aggregate question should succeed`() {
        val aggregate = AggregateBuilder().buildNew()
        val question = QuestionBuilder().build()
        assertEquals(DomainOperationResultEnum.SUCCESS, aggregate.subscriberRequestQuestion(question).result)
    }
}

class AggregateBuilder {
    private var id: UUID = UUID.randomUUID()
    fun withId(id: UUID) = apply { this.id = id }
    fun buildNew(): IChatAggregate = ChatAggregate.create(DefaultAnemicModel.create(id))
}
```
