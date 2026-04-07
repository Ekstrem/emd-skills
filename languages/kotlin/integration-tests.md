# Integration Tests — Kotlin/JVM

> Тесты для Kotlin/JVM микросервиса: JUnit 5, Builder pattern, Ktor testApplication.

## Unit Tests — Aggregate

```kotlin
class AggregateTest {
    @Test fun `subscriber request question on new aggregate should succeed`() {
        val aggregate = AggregateBuilder().buildNew()
        val question = QuestionBuilder().build()
        assertEquals(DomainOperationResultEnum.SUCCESS,
            aggregate.subscriberRequestQuestion(question).result)
    }

    @Test fun `subscriber request question on existing aggregate should fail`() {
        val id = UUID.randomUUID()
        val agg = AggregateBuilder().withId(id).buildNew()
        val r1 = agg.subscriberRequestQuestion(QuestionBuilder().build(id))
        assertEquals(DomainOperationResultEnum.SUCCESS, r1.result)
        val existing = ChatAggregate.create(r1.model)
        val r2 = existing.subscriberRequestQuestion(QuestionBuilder().build(id))
        assertEquals(DomainOperationResultEnum.EXCEPTION, r2.result)
    }
}
```

## Builder Pattern

```kotlin
class AggregateBuilder {
    private var id: UUID = UUID.randomUUID()
    fun withId(id: UUID) = apply { this.id = id }
    fun buildNew(): IChatAggregate = ChatAggregate.create(DefaultAnemicModel.create(id))
}

class QuestionBuilder {
    private var userId: UUID = UUID.randomUUID()
    private var sessionId: Int = 1
    private var login: String = "user1"
    private var messageText: String = "Hello"
    private var platform: Platform = Platform.Windows
    private var application: ChatApplication = ChatApplication.Site

    fun withUserId(id: UUID) = apply { userId = id }
    fun withLogin(l: String) = apply { login = l }

    fun build(aggregateId: UUID = UUID.randomUUID()): IChatAnemicModel =
        ChatAnemicModel.create(
            id = aggregateId, version = 0L,
            correlationToken = UUID.randomUUID(),
            commandName = "SubscriberRequestQuestion",
            subjectName = "SubscriberRequestQuestion",
            root = ChatRoot.createInstance(userId, sessionId),
            actor = ChatActor.createInstance(login, UserType.Client),
            feedback = null,
            messages = listOf(ChatMessage.createInstance(
                MessageType.Text, messageText, platform, application, UUID(0, 0)))
        )
}
```

## Ktor Integration Tests

```kotlin
class ChatRoutesTest {
    @Test fun `POST chat should create session`() = testApplication {
        application {
            install(ContentNegotiation) { json() }
            install(Koin) { modules(testChatModule()) }
            chatRoutes()
        }
        val response = client.post("/api/v1/chat") {
            contentType(ContentType.Application.Json)
            setBody("""{"userId":"...","sessionId":1,"login":"user1","messageText":"Hi"}""")
        }
        assertEquals(HttpStatusCode.OK, response.status)
    }
}

fun testChatModule() = module {
    single<IRepository> { InMemoryRepository() }
    single<EventBus> { InMemoryEventBus() }
    single<BusAdapter> { BusAdapter(get()) }
    single<IChatAggregateProvider> { AggregateProvider(get(), listOf(get<BusAdapter>())) }
}
```

## build.gradle.kts

```kotlin
dependencies {
    testImplementation(project(":chat-domain"))
    testImplementation(libs.junit.jupiter)
    testImplementation(libs.kotlin.test)
}
tasks.test { useJUnitPlatform() }
```
