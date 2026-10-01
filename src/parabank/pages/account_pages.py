"""Операции по счетам: открытие счёта, перевод, поиск транзакций, кредит."""

from __future__ import annotations

import re
from decimal import Decimal

import allure
from playwright.sync_api import Page, expect

from parabank.api.models import AccountType
from parabank.pages.base_page import BasePage


class OpenAccountPage(BasePage):
    path = "openaccount.htm"
    title = "Open New Account"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.type_select = page.locator("#type")
        self.from_select = page.locator("#fromAccountId")
        self.open_button = page.locator("input[value='Open New Account']")
        self.result_heading = page.locator("#openAccountResult h1")
        self.new_account_id = page.locator("#newAccountId")

    def open_account(self, account_type: AccountType, from_account_id: int) -> int:
        with allure.step(f"UI: открыть счёт {account_type} со взносом со счёта {from_account_id}"):
            self.type_select.select_option(label=account_type.value)
            # Список счетов подгружается скриптом; select_option ждёт появления нужного пункта.
            self.from_select.select_option(str(from_account_id))
            self.open_button.click()
            expect(self.new_account_id).to_have_text(re.compile(r"^\d+$"))
            return int(self.new_account_id.inner_text())


class TransferPage(BasePage):
    path = "transfer.htm"
    title = "Transfer Funds"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.amount = page.locator("#amount")
        self.from_select = page.locator("#fromAccountId")
        self.to_select = page.locator("#toAccountId")
        self.transfer_button = page.locator("input[value='Transfer']")
        self.result_heading = page.locator("#showResult h1")
        self.result_amount = page.locator("#amountResult")
        self.result_from = page.locator("#fromAccountIdResult")
        self.result_to = page.locator("#toAccountIdResult")
        self.internal_error = page.locator("#showError")
        self.amount_required = page.get_by_text("The amount cannot be empty.")

    def transfer(self, amount: Decimal | str, from_account_id: int, to_account_id: int) -> None:
        with allure.step(f"UI: перевод {amount} со счёта {from_account_id} на {to_account_id}"):
            self.from_select.select_option(str(from_account_id))
            self.to_select.select_option(str(to_account_id))
            self.amount.fill(str(amount))
            self.transfer_button.click()


class FindTransactionsPage(BasePage):
    path = "findtrans.htm"
    title = "Find Transactions"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.account_select = page.locator("#accountId")
        self.amount = page.locator("#amount")
        self.find_by_amount_button = page.locator("#findByAmount")
        self.rows = page.locator("#transactionTable tbody tr")

    def find_by_amount(self, account_id: int, amount: Decimal) -> None:
        with allure.step(f"UI: поиск транзакций на {amount} по счёту {account_id}"):
            self.account_select.select_option(str(account_id))
            self.amount.fill(str(amount))
            self.find_by_amount_button.click()


class RequestLoanPage(BasePage):
    path = "requestloan.htm"
    title = "Apply for a Loan"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.amount = page.locator("#amount")
        self.down_payment = page.locator("#downPayment")
        self.from_select = page.locator("#fromAccountId")
        self.apply_button = page.locator("input[value='Apply Now']")
        self.status = page.locator("#loanStatus")
        self.new_account_id = page.locator("#loanRequestApproved #newAccountId")
        self.denied_message = page.locator("#loanRequestDenied")

    def apply(self, amount: Decimal, down_payment: Decimal, from_account_id: int) -> None:
        with allure.step(f"UI: заявка на кредит {amount}, первый взнос {down_payment}"):
            self.amount.fill(str(amount))
            self.down_payment.fill(str(down_payment))
            self.from_select.select_option(str(from_account_id))
            self.apply_button.click()
