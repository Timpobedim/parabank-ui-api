"""Счета через REST API: открытие счёта, пополнение и снятие, история операций."""

from __future__ import annotations

from decimal import Decimal

import pytest

from parabank.api.client import ParaBankApi
from parabank.api.models import Account, AccountType, TransactionType
from parabank.api.registration import RegisteredCustomer

pytestmark = pytest.mark.api

OPENING_DEPOSIT = Decimal("100.00")


@pytest.mark.sanity
def test_open_savings_account_moves_opening_deposit(
    api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    savings = api.create_account(customer.customer_id, AccountType.SAVINGS, checking_account.id)

    balances = {account.id: account.balance for account in api.get_accounts(customer.customer_id)}
    assert balances == {
        checking_account.id: checking_account.balance - OPENING_DEPOSIT,
        savings.id: OPENING_DEPOSIT,
    }
    [deposit] = api.get_transactions(savings.id)
    assert (deposit.type, deposit.amount, deposit.description) == (
        TransactionType.CREDIT,
        OPENING_DEPOSIT,
        "Funds Transfer Received",
    )


def test_deposit_and_withdraw_change_balance(api: ParaBankApi, checking_account: Account) -> None:
    account_id = checking_account.id

    deposited = api.deposit(account_id, Decimal("200"))
    withdrawn = api.withdraw(account_id, Decimal("20"))

    assert deposited == f"Successfully deposited $200 to account #{account_id}"
    assert withdrawn == f"Successfully withdrew $20 from account #{account_id}"
    assert api.get_account(account_id).balance == checking_account.balance + Decimal("180")
    history = [(item.type, item.amount, item.description) for item in api.get_transactions(account_id)]
    assert history == [
        (TransactionType.CREDIT, Decimal("200"), "Deposit via Web Service"),
        (TransactionType.DEBIT, Decimal("20"), "Withdraw via Web Service"),
    ]


def test_unknown_account_is_reported(api: ParaBankApi) -> None:
    response = api.request("GET", "/accounts/999999999")

    # Статус проверяет test_unknown_account_returns_404 (дефект PB-004), здесь — текст ошибки.
    assert response.status_code >= 400
    assert response.text == "Could not find account #999999999"
