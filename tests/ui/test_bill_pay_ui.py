"""Оплата счетов через интерфейс: валидация формы и успешный платёж."""

from __future__ import annotations

from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from parabank.api.models import Account
from parabank.data.factories import new_payee
from parabank.pages.service_pages import BillPayPage

pytestmark = pytest.mark.ui

REQUIRED_MESSAGES = [
    "Payee name is required.",
    "Address is required.",
    "City is required.",
    "State is required.",
    "Zip Code is required.",
    "Phone number is required.",
    "Account number is required.",
    "Account number is required.",
    "The amount cannot be empty.",
]


def test_empty_form_shows_required_messages(customer_page: Page) -> None:
    bill_pay = BillPayPage(customer_page).open().should_be_opened()

    bill_pay.send()

    expect(bill_pay.visible_errors).to_have_text(REQUIRED_MESSAGES)


def test_account_numbers_must_match(customer_page: Page, checking_account: Account) -> None:
    payee = new_payee()
    bill_pay = BillPayPage(customer_page).open()

    bill_pay.fill(payee, Decimal("25"), checking_account.id, verify_account=payee.account_number + 1)
    bill_pay.send()

    expect(bill_pay.visible_errors).to_have_text(["The account numbers do not match."])


@pytest.mark.sanity
def test_successful_payment(customer_page: Page, checking_account: Account) -> None:
    payee = new_payee()
    bill_pay = BillPayPage(customer_page).open()

    bill_pay.fill(payee, Decimal("25"), checking_account.id)
    bill_pay.send()

    expect(bill_pay.result_heading).to_have_text("Bill Payment Complete")
    expect(bill_pay.result_text).to_have_text(
        f"Bill Payment to {payee.name} in the amount of $25.00 "
        f"from account {checking_account.id} was successful."
    )
