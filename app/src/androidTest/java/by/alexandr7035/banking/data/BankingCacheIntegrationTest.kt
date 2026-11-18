package by.alexandr7035.banking.data

import androidx.paging.PagingSource
import androidx.room.Room
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import by.alexandr7035.banking.data.account.AccountRepositoryMock
import by.alexandr7035.banking.data.cards.cache.CardEntity
import by.alexandr7035.banking.data.db.CacheDatabase
import by.alexandr7035.banking.data.db.convertors.MoneyAmountConvertor
import by.alexandr7035.banking.data.transactions.TransactionSource
import by.alexandr7035.banking.data.transactions.db.TransactionEntity
import by.alexandr7035.banking.domain.core.AppError
import by.alexandr7035.banking.domain.core.ErrorType
import by.alexandr7035.banking.domain.features.account.model.MoneyAmount
import by.alexandr7035.banking.domain.features.cards.model.CardType
import by.alexandr7035.banking.domain.features.transactions.model.TransactionStatus
import by.alexandr7035.banking.domain.features.transactions.model.TransactionType
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class BankingCacheIntegrationTest {
    private lateinit var db: CacheDatabase

    @Before
    fun openDatabase() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        db = Room.inMemoryDatabaseBuilder(context, CacheDatabase::class.java)
            .addTypeConverter(MoneyAmountConvertor())
            .build()
    }

    @After
    fun closeDatabase() {
        db.close()
    }

    @Test
    fun historicoSemFiltroMostraLancamentosDoMaisRecenteAoMaisAntigo() = runBlocking {
        val send = insert(TransactionType.SEND)
        val topUp = insert(TransactionType.TOP_UP)
        val receive = insert(TransactionType.RECEIVE)

        assertEquals(listOf(receive, topUp, send), loadHistory(null).data.map { it.id })
    }

    @Test
    fun filtroRetornaSomenteLancamentosDoTipoSelecionado() = runBlocking {
        val firstSend = insert(TransactionType.SEND)
        val topUp = insert(TransactionType.TOP_UP)
        val receive = insert(TransactionType.RECEIVE)
        val secondSend = insert(TransactionType.SEND)

        assertEquals(
            listOf(secondSend, firstSend),
            loadHistory(TransactionType.SEND).data.map { it.id },
        )
        assertEquals(listOf(topUp), loadHistory(TransactionType.TOP_UP).data.map { it.id })
        assertEquals(listOf(receive), loadHistory(TransactionType.RECEIVE).data.map { it.id })
    }

    @Test
    fun filtroSemResultadosRetornaPaginaVaziaSemProximaPagina() = runBlocking {
        insert(TransactionType.TOP_UP)

        val page = loadHistory(TransactionType.SEND)

        assertEquals(emptyList<TransactionEntity>(), page.data)
        assertNull(page.nextKey)
    }

    @Test
    fun saldoAgregadoEConsultaPorCartaoUsamDadosDoCache() = runBlocking {
        val cardsDao = db.getCardsDao()
        cardsDao.addCard(card("cartao-a", 25.5f))
        cardsDao.addCard(card("cartao-b", 14.5f))
        val repository = AccountRepositoryMock(Dispatchers.IO, cardsDao)

        withTimeout(5_000) {
            assertEquals(MoneyAmount(40f), repository.getBalanceFlow().first())
            assertEquals(MoneyAmount(14.5f), repository.getCardBalanceFlow("cartao-b").first())
        }
    }

    @Test
    fun envioAcimaDoSaldoPreservaCartao() = runBlocking {
        val cardsDao = db.getCardsDao()
        val source = card("origem", 25f)
        cardsDao.addCard(source)
        val repository = AccountRepositoryMock(Dispatchers.IO, cardsDao)

        val error = runCatching { repository.sendFromCard(source.number, MoneyAmount(25.5f), 1L) }

        assertEquals(AppError(ErrorType.INSUFFICIENT_CARD_BALANCE), error.exceptionOrNull())
        assertEquals(source, cardsDao.getCardByNumber(source.number))
    }

    @Test
    fun envioComCartaoRemovidoPreservaOutrosCartoes() = runBlocking {
        val cardsDao = db.getCardsDao()
        val source = card("origem", 25f)
        val other = card("outro", 10f)
        cardsDao.addCard(source)
        cardsDao.addCard(other)
        cardsDao.deleteCard(source)
        val repository = AccountRepositoryMock(Dispatchers.IO, cardsDao)

        val error = runCatching { repository.sendFromCard(source.number, MoneyAmount(5f), 1L) }

        assertEquals(AppError(ErrorType.CARD_NOT_FOUND), error.exceptionOrNull())
        assertEquals(listOf(other), cardsDao.getCards())
    }

    @Test
    fun envioNoValorExatoDoSaldoZeraCartaoDeOrigem() = runBlocking {
        val cardsDao = db.getCardsDao()
        val source = card("origem", 25.5f)
        cardsDao.addCard(source)
        val repository = AccountRepositoryMock(Dispatchers.IO, cardsDao)

        repository.sendFromCard(source.number, MoneyAmount(25.5f), 1L)

        assertEquals(source.copy(recentBalance = 0f), cardsDao.getCardByNumber(source.number))
    }

    @Test
    fun envioComValorNaoPositivoOuNaoFinitoPreservaCartao() = runBlocking {
        val cardsDao = db.getCardsDao()
        val source = card("origem", 25f)
        cardsDao.addCard(source)
        val repository = AccountRepositoryMock(Dispatchers.IO, cardsDao)

        for (amount in listOf(0f, -1f, Float.NaN, Float.POSITIVE_INFINITY)) {
            val error = runCatching { repository.sendFromCard(source.number, MoneyAmount(amount), 1L) }

            assertEquals("Valor: $amount", AppError(ErrorType.GENERIC_VALIDATION_ERROR), error.exceptionOrNull())
            assertEquals("Valor: $amount", source, cardsDao.getCardByNumber(source.number))
        }
    }

    private fun card(number: String, balance: Float) = CardEntity(
        number = number,
        isPrimary = false,
        cardType = CardType.DEBIT,
        recentBalance = balance,
        cardHolder = "Perfil sintético",
        expiration = 1_900_000_000_000L,
        addressFirstLine = "",
        addressSecondLine = "",
        addedDate = 1_700_000_000_000L,
    )

    private suspend fun loadHistory(type: TransactionType?): PagingSource.LoadResult.Page<Int, TransactionEntity> {
        val source = TransactionSource(db.getTransactionsDao(), type)
        val params = PagingSource.LoadParams.Refresh<Int>(
            key = null,
            loadSize = 10,
            placeholdersEnabled = false,
        )
        return when (val result = source.load(params)) {
            is PagingSource.LoadResult.Page -> result
            is PagingSource.LoadResult.Error -> throw AssertionError("Falha ao carregar o histórico", result.throwable)
            is PagingSource.LoadResult.Invalid -> throw AssertionError("Fonte do histórico inválida")
        }
    }

    private suspend fun insert(type: TransactionType): Long =
        db.getTransactionsDao().addTransaction(
            TransactionEntity(
                type = type,
                value = MoneyAmount(10f),
                recentStatus = TransactionStatus.COMPLETED,
                cardId = "cartao-sintetico",
                createdDate = 1_700_000_000_000L,
                updatedStatusDate = 1_700_000_000_000L,
            ),
        )
}
