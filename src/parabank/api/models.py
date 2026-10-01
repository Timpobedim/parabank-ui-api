"""Pydantic-модели ответов REST API ParaBank.

В OpenAPI ParaBank у всех операций описан только ответ default, поэтому контракт ответов
фиксируется здесь. extra="forbid": новое или переименованное поле в ответе роняет тест —
это и есть контроль контракта, а не молчаливое игнорирование.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)


class AccountType(StrEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    LOAN = "LOAN"


class TransactionType(StrEnum):
    CREDIT = "Credit"
    DEBIT = "Debit"


class Address(ApiModel):
    street: str
    city: str
    state: str
    zip_code: str = Field(alias="zipCode")


class Customer(ApiModel):
    id: int
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    address: Address
    phone_number: str = Field(alias="phoneNumber")
    ssn: str


class Account(ApiModel):
    id: int
    customer_id: int = Field(alias="customerId")
    type: AccountType
    balance: Decimal


class Transaction(ApiModel):
    id: int
    account_id: int = Field(alias="accountId")
    type: TransactionType
    date: datetime  # в ответе — миллисекунды Unix-времени
    amount: Decimal
    description: str


class Payee(ApiModel):
    name: str
    address: Address
    phone_number: str = Field(alias="phoneNumber")
    account_number: int = Field(alias="accountNumber")


class BillPayResult(ApiModel):
    payee_name: str = Field(alias="payeeName")
    amount: Decimal
    account_id: int = Field(alias="accountId")


class LoanResponse(ApiModel):
    response_date: datetime = Field(alias="responseDate")
    loan_provider_name: str = Field(alias="loanProviderName")
    approved: bool
    message: str | None = None  # есть только у отказа
    account_id: int | None = Field(alias="accountId")
