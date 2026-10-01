from __future__ import annotations

import pytest

from parabank.api.client import ParaBankApi
from parabank.api.models import Account, AccountType
from parabank.api.registration import RegisteredCustomer


@pytest.fixture
def savings_account(api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account) -> Account:
    """Второй счёт клиента: SAVINGS, открывается переводом $100 с основного счёта."""
    return api.create_account(customer.customer_id, AccountType.SAVINGS, checking_account.id)
