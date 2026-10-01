"""Клиенты банка через REST API: вход, профиль, стартовый счёт."""

from __future__ import annotations

from decimal import Decimal

import pytest

from parabank.api.client import ParaBankApi
from parabank.api.models import AccountType
from parabank.api.registration import RegisteredCustomer

pytestmark = pytest.mark.api

WELCOME_BALANCE = Decimal("515.50")


@pytest.mark.sanity
def test_login_returns_customer_profile(api: ParaBankApi, customer: RegisteredCustomer) -> None:
    profile = api.login(customer.username, customer.password)

    assert profile.id == customer.customer_id
    assert (profile.first_name, profile.last_name) == (
        customer.profile.first_name,
        customer.profile.last_name,
    )
    assert profile.address.city == customer.profile.city


def test_login_with_wrong_password_is_rejected(api: ParaBankApi, customer: RegisteredCustomer) -> None:
    response = api.request("GET", f"/login/{customer.username}/wrong-password")

    assert response.status_code == 400
    assert response.text == "Invalid username and/or password"


def test_new_customer_gets_checking_account_with_welcome_balance(
    api: ParaBankApi, customer: RegisteredCustomer
) -> None:
    accounts = api.get_accounts(customer.customer_id)

    assert [(account.type, account.balance) for account in accounts] == [
        (AccountType.CHECKING, WELCOME_BALANCE)
    ]


def test_update_contact_info(api: ParaBankApi, customer: RegisteredCustomer) -> None:
    profile = api.get_customer(customer.customer_id)
    updated = profile.model_copy(
        update={
            "address": profile.address.model_copy(update={"city": "Самара", "street": "Московское шоссе, 1"}),
            "phone_number": "88462000000",
        }
    )

    message = api.update_customer(updated, customer.username, customer.password)

    assert message == "Successfully updated customer profile"
    assert api.get_customer(customer.customer_id) == updated
