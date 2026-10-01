"""Тестовые данные. У каждого теста свой клиент с уникальным логином — общих учётных записей
нет, поэтому тесты не зависят друг от друга и запускаются параллельно.

По умолчанию клиенты — с русскими именами и адресами: через HTTP-форму в UTF-8 ParaBank хранит
кириллицу корректно. Для ввода в браузере нужен latin=True — страницы ParaBank в ISO-8859-1,
и кириллица из браузерной формы сохраняется HTML-сущностями (дефект PB-010).
Телефон — только цифры: «+» ломается при обновлении профиля через API (дефект PB-006).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace

from faker import Faker

from parabank.api.models import Address, Payee

_RU = Faker("ru_RU")
_EN = Faker("en_US")

PASSWORD = "Secret-123"

# Предельные длины полей формы регистрации, найденные исследованием стенда. Значение длиннее —
# и ParaBank отказывает с ложной ошибкой «This username already exists.» (дефект PB-011).
FIELD_LIMITS = {
    "first_name": 30,
    "last_name": 30,
    "street": 45,
    "city": 20,
    "state": 20,
    "zip_code": 20,
    "phone_number": 20,
    "ssn": 15,
    "username": 20,
    "password": 20,
}


def _fit(make: Callable[[], str], limit: int) -> str:
    """Faker иногда выдаёт длинные значения («Петропавловск-Камчатский») — берём подходящее."""
    for _ in range(100):
        value = make()
        if len(value) <= limit:
            return value
    raise ValueError(f"Faker не сгенерировал значение не длиннее {limit} символов")


@dataclass(frozen=True)
class NewCustomer:
    first_name: str
    last_name: str
    street: str
    city: str
    state: str
    zip_code: str
    phone_number: str
    ssn: str
    username: str
    password: str

    def form_data(self, repeated_password: str | None = None) -> dict[str, str]:
        """Поля формы register.htm; repeated_password — чтобы проверить несовпадение паролей."""
        return {
            "customer.firstName": self.first_name,
            "customer.lastName": self.last_name,
            "customer.address.street": self.street,
            "customer.address.city": self.city,
            "customer.address.state": self.state,
            "customer.address.zipCode": self.zip_code,
            "customer.phoneNumber": self.phone_number,
            "customer.ssn": self.ssn,
            "customer.username": self.username,
            "customer.password": self.password,
            "repeatedPassword": self.password if repeated_password is None else repeated_password,
        }


def unique_username() -> str:
    return f"qa_{uuid.uuid4().hex[:12]}"


def new_customer(*, latin: bool = False, **overrides: str) -> NewCustomer:
    fake = _EN if latin else _RU
    customer = NewCustomer(
        first_name=_fit(fake.first_name_female, FIELD_LIMITS["first_name"]),
        last_name=_fit(fake.last_name_female, FIELD_LIMITS["last_name"]),
        street=_fit(lambda: f"{fake.street_name()}, {fake.building_number()}", FIELD_LIMITS["street"]),
        city=_fit(fake.city if latin else fake.city_name, FIELD_LIMITS["city"]),
        state=fake.random_element(("MO", "SP", "TA", "NS", "SV")),
        zip_code=fake.postcode(),
        phone_number="8" + fake.numerify("##########"),
        ssn=fake.numerify("###-##-####"),
        username=unique_username(),
        password=PASSWORD,
    )
    return replace(customer, **overrides)


def new_payee() -> Payee:
    """Получатель платежа. Форма оплаты отправляет JSON в UTF-8, поэтому кириллица здесь безопасна."""
    return Payee(
        name=_RU.company(),
        address=Address(
            street=f"{_RU.street_name()}, {_RU.building_number()}",
            city=_RU.city_name(),
            state="MO",
            zip_code=_RU.postcode(),
        ),
        phone_number="8" + _RU.numerify("##########"),
        account_number=int(_RU.numerify("#######")),
    )
