"""Сценарии, где UI и API работают вместе.

Данные готовятся через API (быстро и без хрупких кликов), а проверяется то, что видит
пользователь, — и наоборот: действие в интерфейсе проверяется по состоянию в API.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from parabank.api.client import ParaBankApi
from parabank.api.models import Account, AccountType, TransactionType
from parabank.api.registration import RegisteredCustomer
from parabank.data.factories import new_customer, new_payee
from parabank.pages.account_pages import FindTransactionsPage, TransferPage
from parabank.pages.auth_pages import RegisterPage
from parabank.pages.overview_page import OverviewPage
from parabank.pages.service_pages import UpdateProfilePage

pytestmark = pytest.mark.e2e


@pytest.mark.sanity
def test_account_opened_via_api_appears_in_ui(
    api: ParaBankApi, customer: RegisteredCustomer, customer_page: Page, checking_account: Account
) -> None:
    savings = api.create_account(customer.customer_id, AccountType.SAVINGS, checking_account.id)

    overview = OverviewPage(customer_page).open().should_be_opened()

    expect(overview.balance_of(savings.id)).to_have_text("$100.00")
    expect(overview.balance_of(checking_account.id)).to_have_text("$415.50")


def test_transfer_made_in_ui_is_visible_via_api(
    api: ParaBankApi, customer: RegisteredCustomer, customer_page: Page, checking_account: Account
) -> None:
    savings = api.create_account(customer.customer_id, AccountType.SAVINGS, checking_account.id)
    transfer = TransferPage(customer_page).open().should_be_opened()

    transfer.transfer(Decimal("40"), checking_account.id, savings.id)

    expect(transfer.result_heading).to_have_text("Transfer Complete!")
    assert api.get_account(savings.id).balance == Decimal("140.00")
    [sent] = api.find_transactions_by_amount(checking_account.id, Decimal("40"))
    assert (sent.type, sent.description) == (TransactionType.DEBIT, "Funds Transfer Sent")


def test_bill_paid_via_api_is_found_in_ui(
    api: ParaBankApi, customer_page: Page, checking_account: Account
) -> None:
    payee = new_payee()
    api.pay_bill(checking_account.id, Decimal("33.30"), payee)
    search = FindTransactionsPage(customer_page).open().should_be_opened()

    search.find_by_amount(checking_account.id, Decimal("33.30"))

    expect(search.rows).to_have_count(1)
    expect(search.rows.first).to_contain_text(f"Bill Payment to {payee.name}")
    expect(search.rows.first).to_contain_text("$33.30")


def test_profile_updated_in_ui_is_returned_by_api(
    api: ParaBankApi, customer: RegisteredCustomer, customer_page: Page
) -> None:
    profile_page = UpdateProfilePage(customer_page).open().should_be_opened()

    profile_page.update({"customer.address.city": "Самара", "customer.phoneNumber": "88462000000"})

    expect(profile_page.result_heading).to_have_text("Profile Updated")
    profile = api.get_customer(customer.customer_id)
    assert (profile.address.city, profile.phone_number) == ("Самара", "88462000000")


def test_customer_registered_in_ui_can_log_in_via_api(page: Page, api: ParaBankApi) -> None:
    profile = new_customer(latin=True)
    register_page = RegisterPage(page).open()

    register_page.fill(profile)
    register_page.submit()

    expect(register_page.heading).to_have_text(f"Welcome {profile.username}")
    customer = api.login(profile.username, profile.password)
    assert (customer.first_name, customer.address.city) == (profile.first_name, profile.city)
