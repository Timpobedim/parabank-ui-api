"""Переводы, оплата счетов и кредиты через REST API."""

from __future__ import annotations

from decimal import Decimal

import pytest

from parabank.api.client import ParaBankApi
from parabank.api.models import Account, AccountType, BillPayResult, TransactionType
from parabank.api.registration import RegisteredCustomer
from parabank.data.factories import new_payee

pytestmark = pytest.mark.api


@pytest.mark.sanity
def test_transfer_moves_money_and_records_both_sides(
    api: ParaBankApi, checking_account: Account, savings_account: Account
) -> None:
    message = api.transfer(checking_account.id, savings_account.id, Decimal("50"))

    assert message == (
        f"Successfully transferred $50 from account #{checking_account.id} to account #{savings_account.id}"
    )
    assert api.get_account(savings_account.id).balance == Decimal("150.00")
    [sent] = api.find_transactions_by_amount(checking_account.id, Decimal("50"))
    [received] = api.find_transactions_by_amount(savings_account.id, Decimal("50"))
    assert (sent.type, sent.description) == (TransactionType.DEBIT, "Funds Transfer Sent")
    assert (received.type, received.description) == (TransactionType.CREDIT, "Funds Transfer Received")


def test_bill_payment_debits_account(api: ParaBankApi, checking_account: Account) -> None:
    payee = new_payee()

    result = api.pay_bill(checking_account.id, Decimal("30"), payee)

    assert result == BillPayResult(
        payee_name=payee.name, amount=Decimal("30"), account_id=checking_account.id
    )
    assert api.get_account(checking_account.id).balance == checking_account.balance - Decimal("30")
    [payment] = api.find_transactions_by_amount(checking_account.id, Decimal("30"))
    assert (payment.type, payment.description) == (TransactionType.DEBIT, f"Bill Payment to {payee.name}")


def test_loan_is_approved_and_opens_loan_account(
    api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    loan = api.request_loan(customer.customer_id, Decimal("1000"), Decimal("100"), checking_account.id)

    assert loan.approved
    assert loan.account_id is not None
    loan_account = api.get_account(loan.account_id)
    assert (loan_account.type, loan_account.balance) == (AccountType.LOAN, Decimal("1000.00"))
    [down_payment] = api.find_transactions_by_amount(checking_account.id, Decimal("100"))
    assert down_payment.description == f"Down Payment for Loan # {loan.account_id}"


def test_loan_is_denied_without_funds_for_down_payment(
    api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    # Первый взнос $600 больше остатка $515.50.
    loan = api.request_loan(customer.customer_id, Decimal("1000"), Decimal("600"), checking_account.id)

    assert not loan.approved
    assert loan.account_id is None
    assert [account.id for account in api.get_accounts(customer.customer_id)] == [checking_account.id]
