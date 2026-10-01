"""REST-клиент ParaBank на requests.

Клиент не содержит assert: он отправляет запросы и возвращает
типизированные модели, а проверки живут в тестах. Каждый запрос — шаг Allure с вложенными
запросом и ответом, поэтому по отчёту видно, что именно ушло на сервер.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from urllib.parse import quote

import allure
import requests
from pydantic import TypeAdapter

from parabank.api.models import (
    Account,
    AccountType,
    BillPayResult,
    Customer,
    LoanResponse,
    Payee,
    Transaction,
)

_ACCOUNTS = TypeAdapter(list[Account])
_TRANSACTIONS = TypeAdapter(list[Transaction])
# Коды типа счёта в параметре newAccountType — те же, что в форме открытия счёта.
_ACCOUNT_TYPE_CODES = {AccountType.CHECKING: 0, AccountType.SAVINGS: 1, AccountType.LOAN: 2}


class ParaBankApiError(Exception):
    def __init__(self, response: requests.Response) -> None:
        super().__init__(
            f"{response.request.method} {response.url} → {response.status_code}: {response.text[:200]}"
        )
        self.status_code = response.status_code
        self.text = response.text


class ParaBankApi:
    def __init__(self, api_url: str, timeout: float) -> None:
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        # Без Accept: application/json ParaBank отвечает XML.
        self._session.headers["Accept"] = "application/json"

    def close(self) -> None:
        self._session.close()

    def request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: Any = None
    ) -> requests.Response:
        """Запрос без проверки статуса — для негативных тестов, где важен сам ответ."""
        with allure.step(f"API: {method} {path}"):
            response = self._session.request(
                method, f"{self._api_url}{path}", params=params, json=json_body, timeout=self._timeout
            )
            _attach(response, json_body)
        return response

    def _call(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: Any = None
    ) -> requests.Response:
        response = self.request(method, path, params=params, json_body=json_body)
        if not response.ok:
            raise ParaBankApiError(response)
        return response

    # --- клиенты ---

    def login(self, username: str, password: str) -> Customer:
        path = f"/login/{quote(username, safe='')}/{quote(password, safe='')}"
        return Customer.model_validate(self._call("GET", path).json())

    def get_customer(self, customer_id: int) -> Customer:
        return Customer.model_validate(self._call("GET", f"/customers/{customer_id}").json())

    def update_customer(self, customer: Customer, username: str, password: str) -> str:
        params = {
            "firstName": customer.first_name,
            "lastName": customer.last_name,
            "street": customer.address.street,
            "city": customer.address.city,
            "state": customer.address.state,
            "zipCode": customer.address.zip_code,
            "phoneNumber": customer.phone_number,
            "ssn": customer.ssn,
            "username": username,
            "password": password,
        }
        return self._call("POST", f"/customers/update/{customer.id}", params=params).text

    # --- счета ---

    def get_accounts(self, customer_id: int) -> list[Account]:
        return _ACCOUNTS.validate_python(self._call("GET", f"/customers/{customer_id}/accounts").json())

    def get_account(self, account_id: int) -> Account:
        return Account.model_validate(self._call("GET", f"/accounts/{account_id}").json())

    def create_account(self, customer_id: int, account_type: AccountType, from_account_id: int) -> Account:
        params = {
            "customerId": customer_id,
            "newAccountType": _ACCOUNT_TYPE_CODES[account_type],
            "fromAccountId": from_account_id,
        }
        return Account.model_validate(self._call("POST", "/createAccount", params=params).json())

    # --- операции ---

    def transfer(self, from_account_id: int, to_account_id: int, amount: Decimal) -> str:
        params = {"fromAccountId": from_account_id, "toAccountId": to_account_id, "amount": str(amount)}
        return self._call("POST", "/transfer", params=params).text

    def deposit(self, account_id: int, amount: Decimal) -> str:
        return self._call("POST", "/deposit", params={"accountId": account_id, "amount": str(amount)}).text

    def withdraw(self, account_id: int, amount: Decimal) -> str:
        return self._call("POST", "/withdraw", params={"accountId": account_id, "amount": str(amount)}).text

    def pay_bill(self, account_id: int, amount: Decimal, payee: Payee) -> BillPayResult:
        response = self._call(
            "POST",
            "/billpay",
            params={"accountId": account_id, "amount": str(amount)},
            json_body=payee.model_dump(by_alias=True, mode="json"),
        )
        return BillPayResult.model_validate(response.json())

    def request_loan(
        self, customer_id: int, amount: Decimal, down_payment: Decimal, from_account_id: int
    ) -> LoanResponse:
        params = {
            "customerId": customer_id,
            "amount": str(amount),
            "downPayment": str(down_payment),
            "fromAccountId": from_account_id,
        }
        return LoanResponse.model_validate(self._call("POST", "/requestLoan", params=params).json())

    # --- история ---

    def get_transactions(self, account_id: int) -> list[Transaction]:
        return _TRANSACTIONS.validate_python(self._call("GET", f"/accounts/{account_id}/transactions").json())

    def find_transactions_by_amount(self, account_id: int, amount: Decimal) -> list[Transaction]:
        path = f"/accounts/{account_id}/transactions/amount/{amount}"
        return _TRANSACTIONS.validate_python(self._call("GET", path).json())


def _attach(response: requests.Response, json_body: Any) -> None:
    request = response.request
    body = json.dumps(json_body, ensure_ascii=False, indent=2) if json_body is not None else ""
    allure.attach(
        f"{request.method} {request.url}\n\n{body}",
        name="запрос",
        attachment_type=allure.attachment_type.TEXT,
    )
    allure.attach(
        f"{response.status_code} {response.headers.get('Content-Type', '')}\n\n{response.text}",
        name="ответ",
        attachment_type=allure.attachment_type.TEXT,
    )
