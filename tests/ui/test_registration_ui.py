"""Регистрация через интерфейс: успешная, обязательные поля, совпадение паролей, уникальность логина.

Данные — латиницей: кириллицу браузерная форма ParaBank портит (PB-010, см. test_encoding_ui.py).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from parabank.api.registration import RegisteredCustomer
from parabank.data.factories import new_customer
from parabank.pages.auth_pages import RegisterPage

pytestmark = pytest.mark.ui

# Телефон — единственное необязательное поле формы.
REQUIRED_FIELD_ERRORS = {
    "customer.firstName": "First name is required.",
    "customer.lastName": "Last name is required.",
    "customer.address.street": "Address is required.",
    "customer.address.city": "City is required.",
    "customer.address.state": "State is required.",
    "customer.address.zipCode": "Zip Code is required.",
    "customer.ssn": "Social Security Number is required.",
    "customer.username": "Username is required.",
    "customer.password": "Password is required.",
    "repeatedPassword": "Password confirmation is required.",
}


@pytest.fixture
def register_page(page: Page) -> RegisterPage:
    return RegisterPage(page).open().should_be_opened()


@pytest.mark.sanity
def test_register_new_customer(register_page: RegisterPage) -> None:
    profile = new_customer(latin=True)

    register_page.fill(profile)
    register_page.submit()

    expect(register_page.heading).to_have_text(f"Welcome {profile.username}")
    expect(register_page.success_text).to_be_visible()
    expect(register_page.menu.link("Log Out")).to_be_visible()


@pytest.mark.parametrize(
    ("field_id", "message"), list(REQUIRED_FIELD_ERRORS.items()), ids=list(REQUIRED_FIELD_ERRORS)
)
def test_required_field(register_page: RegisterPage, field_id: str, message: str) -> None:
    register_page.fill(new_customer(latin=True))
    register_page.field(field_id).fill("")

    register_page.submit()

    expect(register_page.error_for(field_id)).to_have_text(message)
    expect(register_page.heading).to_have_text(RegisterPage.title)


def test_passwords_must_match(register_page: RegisterPage) -> None:
    register_page.fill(new_customer(latin=True), repeated_password="Other-456")

    register_page.submit()

    expect(register_page.error_for("repeatedPassword")).to_have_text("Passwords did not match.")


def test_username_must_be_unique(register_page: RegisterPage, customer: RegisteredCustomer) -> None:
    register_page.fill(new_customer(latin=True, username=customer.username))

    register_page.submit()

    expect(register_page.error_for("customer.username")).to_have_text("This username already exists.")
