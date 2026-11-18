package by.alexandr7035.banking.domain

import by.alexandr7035.banking.domain.core.AppError
import by.alexandr7035.banking.domain.core.ErrorType
import by.alexandr7035.banking.domain.features.account.model.MoneyAmount
import by.alexandr7035.banking.domain.features.account.send_money.SendMoneyUseCase
import by.alexandr7035.banking.domain.features.transactions.TransactionRepository
import by.alexandr7035.banking.domain.features.transactions.model.TransactionRowPayload
import by.alexandr7035.banking.domain.features.transactions.model.TransactionType
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SendMoneyUseCaseTest {
    private val repository = RecordingTransactionRepository()
    private val useCase = SendMoneyUseCase(repository)

    @Test
    fun valorInvalidoEhRecusadoAntesDoAgendamento() = runBlocking {
        for (amount in listOf(0f, -1f, Float.NaN, Float.POSITIVE_INFINITY)) {
            val result = runCatching { useCase.execute(MoneyAmount(amount), "origem", 1L) }

            assertEquals("Valor: $amount", AppError(ErrorType.GENERIC_VALIDATION_ERROR), result.exceptionOrNull())
        }
        assertTrue(repository.submitted.isEmpty())
    }

    @Test
    fun envioValidoEncaminhaPayloadDeEnvio() = runBlocking {
        val amount = MoneyAmount(5f)

        useCase.execute(amount, "origem", 1L)

        assertEquals(
            listOf(TransactionRowPayload(TransactionType.SEND, amount, "origem", 1L)),
            repository.submitted,
        )
    }

    private class RecordingTransactionRepository : TransactionRepository {
        val submitted = mutableListOf<TransactionRowPayload>()

        override suspend fun submitTransaction(payload: TransactionRowPayload) {
            submitted.add(payload)
        }

        override suspend fun getTransactions(filterByType: TransactionType?) =
            error("Consulta fora do escopo deste teste")

        override fun getTransactionStatusFlow(transactionId: Long) =
            error("Consulta fora do escopo deste teste")
    }
}
