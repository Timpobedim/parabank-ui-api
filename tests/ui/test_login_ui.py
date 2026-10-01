"""Вход и выход через интерфейс."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from parabank.api.registration import RegisteredCustomer
from parabank.pages.auth_pages import HomePage

pytestmark = pytest.mark.ui

NOT_VERIFIED = "The username and password could not be verified."


@pytest.mark.sanity
def test_login_and_logout(page: Page, customer: RegisteredCustomer) -> None:
    home = HomePage(page).open().should_be_opened()

    overview = home.login(customer.username, customer.password).should_be_opened()
    overview.menu.logout()

    home.should_be_opened()


@pytest.mark.parametrize(
    ("username", "password", "error"),
    [
        pytest.param("", "", "Please enter a username and password.", id="empty-form"),
        pytest.param("qa_nobody_404", "wrong-password", NOT_VERIFIED, id="unknown-user"),
    ],
)
def test_login_errors(page: Page, username: str, password: str, error: str) -> None:
    home = HomePage(page).open()

    home.submit(username, password)

    expect(home.error).to_have_text(error)


def test_wrong_password_for_existing_customer(page: Page, customer: RegisteredCustomer) -> None:
    home = HomePage(page).open()

    home.submit(customer.username, "wrong-password")

    expect(home.error).to_have_text(NOT_VERIFIED)
