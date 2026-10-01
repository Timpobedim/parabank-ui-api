"""Счета и операции в личном кабинете. Клиент входит по cookie сессии — форма входа проверяется
в test_login_ui.py, а здесь тест сразу начинается со страницы, которую проверяет."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from parabank.api.client import ParaBankApi
from parabank.api.models import Account, AccountType
from parabank.api.registration import RegisteredCustomer
from parabank.pages.account_pages import OpenAccountPage, RequestLoanPage, TransferPage
from parabank.pages.overview_page import OverviewPage

pytestmark = pytest.mark.ui

DEFECT_TIMEOUT_MS = 3_000


@pytest.mark.sanity
def test_overview_shows_welcome_balance(customer_page: Page, checking_account: Account) -> None:
    overview = OverviewPage(customer_page).open().should_be_opened()

    expect(overview.balance_of(checking_account.id)).to_have_text("$515.50")


def test_open_savings_account(customer_page: Page, checking_account: Account) -> None:
    new_account_id = (
        OpenAccountPage(customer_page)
        .open()
        .should_be_opened()
        .open_account(AccountType.SAVINGS, checking_account.id)
    )

    overview = OverviewPage(customer_page).open()
    expect(overview.balance_of(new_account_id)).to_have_text("$100.00")
    expect(overview.balance_of(checking_account.id)).to_have_text("$415.50")


def test_transfer_between_own_accounts(
    customer_page: Page, api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    savings = api.create_account(customer.customer_id, AccountType.SAVINGS, checking_account.id)
    transfer = TransferPage(customer_page).open().should_be_opened()

    transfer.transfer(Decimal("25"), checking_account.id, savings.id)

    expect(transfer.result_heading).to_have_text("Transfer Complete!")
    expect(transfer.result_amount).to_have_text("$25.00")
    expect(transfer.result_from).to_have_text(str(checking_account.id))
    expect(transfer.result_to).to_have_text(str(savings.id))


def test_request_loan_is_approved(customer_page: Page, checking_account: Account) -> None:
    loan = RequestLoanPage(customer_page).open().should_be_opened()

    loan.apply(Decimal("1000"), Decimal("100"), checking_account.id)

    expect(loan.status).to_have_text("Approved")
    expect(loan.new_account_id).to_have_text(re.compile(r"^\d+$"))


def test_request_loan_is_denied_without_funds(customer_page: Page, checking_account: Account) -> None:
    loan = RequestLoanPage(customer_page).open()

    loan.apply(Decimal("1000"), Decimal("600"), checking_account.id)

    expect(loan.status).to_have_text("Denied")
    expect(loan.denied_message).to_have_text("You do not have sufficient funds for the given down payment.")


@pytest.mark.known_defect("PB-009", "перевод с пустой суммой: внутренняя ошибка вместо подсказки")
def test_transfer_without_amount_shows_hint(customer_page: Page, checking_account: Account) -> None:
    transfer = TransferPage(customer_page).open().should_be_opened()

    transfer.transfer("", checking_account.id, checking_account.id)

    expect(transfer.amount_required).to_be_visible(timeout=DEFECT_TIMEOUT_MS)
