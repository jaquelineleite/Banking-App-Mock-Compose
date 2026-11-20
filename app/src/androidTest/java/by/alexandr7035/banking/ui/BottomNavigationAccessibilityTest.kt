package by.alexandr7035.banking.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsNotSelected
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import by.alexandr7035.banking.ui.components.bottomnav.M2BottomNavigation
import by.alexandr7035.banking.ui.components.bottomnav.M2BottomNavigationItem
import org.junit.Rule
import org.junit.Test

class BottomNavigationAccessibilityTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun abasExpoemRotuloPapelEAtualizamSelecao() {
        val selected = mutableStateOf("Home")
        compose.setContent {
            M2BottomNavigation {
                listOf("Home", "History").forEach { label ->
                    M2BottomNavigationItem(
                        selected = selected.value == label,
                        onClick = { selected.value = label },
                        icon = {},
                        label = { Text(label) },
                    )
                }
            }
        }

        val tabRole = SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.Tab)
        val home = compose.onNodeWithText("Home")
        val history = compose.onNodeWithText("History")

        home.assert(tabRole).assertIsSelected()
        history.assert(tabRole).assertIsNotSelected()
        history.performClick()
        history.assertIsSelected()
        home.assertIsNotSelected()
    }
}
