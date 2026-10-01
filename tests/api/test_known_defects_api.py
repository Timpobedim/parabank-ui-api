"""Дефекты API, найденные при исследовании стенда.

Каждый тест проверяет ОЖИДАЕМОЕ поведение и помечен known_defect → xfail(strict=True):
пока дефект есть, прогон зелёный; когда его исправят, тест станет XPASS и прогон покраснеет.
Шаги воспроизведения и фактический результат — в docs/bug-reports/.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from functools import partial

import pytest
import requests

from parabank.api.client import ParaBankApi
from parabank.api.models import Account, AccountType
from parabank.api.registration import RegisteredCustomer, try_register
from parabank.config import Settings
from parabank.data.factories import NewCustomer, new_customer

pytestmark = pytest.mark.api

PARALLEL_WRITES = 8


def is_json(text: str) -> bool:
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def registered(settings: Settings, customer: NewCustomer) -> bool:
    """Сетевой сбой в потоке считается неудачной регистрацией, а не ошибкой теста."""
    try:
        return try_register(settings, customer) is not None
    except requests.RequestException:
        return False


@pytest.mark.known_defect("PB-001", "перевод больше остатка проходит, баланс уходит в минус")
def test_transfer_exceeding_balance_is_rejected(
    api: ParaBankApi, checking_account: Account, savings_account: Account
) -> None:
    params = {"fromAccountId": checking_account.id, "toAccountId": savings_account.id, "amount": "100000"}

    response = api.request("POST", "/transfer", params=params)

    assert response.status_code == 400, response.text
    assert api.get_account(checking_account.id).balance >= 0


@pytest.mark.known_defect(
    "PB-002", "перевод на отрицательную сумму проходит — деньги идут в обратную сторону"
)
def test_negative_transfer_amount_is_rejected(
    api: ParaBankApi, checking_account: Account, savings_account: Account
) -> None:
    params = {"fromAccountId": checking_account.id, "toAccountId": savings_account.id, "amount": "-10"}

    response = api.request("POST", "/transfer", params=params)

    assert response.status_code == 400, response.text


@pytest.mark.known_defect("PB-003", "перевод на тот же самый счёт проходит")
def test_transfer_to_the_same_account_is_rejected(api: ParaBankApi, checking_account: Account) -> None:
    params = {"fromAccountId": checking_account.id, "toAccountId": checking_account.id, "amount": "10"}

    response = api.request("POST", "/transfer", params=params)

    assert response.status_code == 400, response.text


@pytest.mark.known_defect("PB-004", "несуществующий счёт — 400 вместо 404")
def test_unknown_account_returns_404(api: ParaBankApi) -> None:
    response = api.request("GET", "/accounts/999999999")

    assert response.status_code == 404


@pytest.mark.known_defect("PB-005", "текстовый ответ объявлен как application/json")
def test_operation_response_matches_content_type(api: ParaBankApi, checking_account: Account) -> None:
    response = api.request("POST", "/deposit", params={"accountId": checking_account.id, "amount": "10"})

    assert response.headers["Content-Type"].startswith("application/json")
    assert is_json(response.text), f"тело ответа — не JSON: {response.text!r}"


@pytest.mark.known_defect("PB-006", "знак + в телефоне при обновлении профиля превращается в пробел")
def test_update_keeps_plus_in_phone_number(api: ParaBankApi, customer: RegisteredCustomer) -> None:
    profile = api.get_customer(customer.customer_id)

    api.update_customer(
        profile.model_copy(update={"phone_number": "+79991234567"}), customer.username, customer.password
    )

    assert api.get_customer(customer.customer_id).phone_number == "+79991234567"


@pytest.mark.known_defect("PB-007", "ответ createAccount показывает баланс 0 вместо зачисленных $100")
def test_created_account_response_shows_actual_balance(
    api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    created = api.create_account(customer.customer_id, AccountType.SAVINGS, checking_account.id)

    assert created.balance == api.get_account(created.id).balance


@pytest.mark.known_defect("PB-008", "отказ в кредите возвращает ключ локализации вместо текста")
def test_loan_denial_message_is_human_readable(
    api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    loan = api.request_loan(customer.customer_id, Decimal("1000"), Decimal("600"), checking_account.id)

    assert loan.message is not None
    assert not re.fullmatch(r"[a-z]+(\.[a-z]+)+", loan.message), f"вместо текста — ключ {loan.message!r}"


@pytest.mark.known_defect(
    "PB-013", "одновременная запись теряется: часть параллельных регистраций отклоняется"
)
def test_parallel_registrations_all_succeed(settings: Settings) -> None:
    customers = [new_customer(latin=True) for _ in range(PARALLEL_WRITES)]

    with ThreadPoolExecutor(max_workers=PARALLEL_WRITES) as pool:
        results = list(pool.map(partial(registered, settings), customers))

    succeeded = sum(results)
    assert succeeded == PARALLEL_WRITES, f"зарегистрировано {succeeded} из {PARALLEL_WRITES}"


@pytest.mark.known_defect("PB-013", "одновременная запись теряется: часть параллельных открытий счёта — 400")
def test_parallel_account_openings_all_succeed(
    settings: Settings, api: ParaBankApi, customer: RegisteredCustomer, checking_account: Account
) -> None:
    api.deposit(checking_account.id, Decimal("10000"))  # денег хватит на все стартовые взносы
    params = {"customerId": customer.customer_id, "newAccountType": 1, "fromAccountId": checking_account.id}

    def open_account(_: int) -> int:
        # Прямой requests, а не общий клиент: requests.Session и шаги Allure не рассчитаны на потоки.
        try:
            response = requests.post(
                f"{settings.api_url}/createAccount",
                params=params,
                headers={"Accept": "application/json"},
                timeout=settings.timeout,
            )
        except requests.RequestException:
            return 0
        return response.status_code

    with ThreadPoolExecutor(max_workers=PARALLEL_WRITES) as pool:
        statuses = list(pool.map(open_account, range(PARALLEL_WRITES)))

    assert statuses.count(200) == PARALLEL_WRITES, f"коды ответов: {sorted(statuses)}"
