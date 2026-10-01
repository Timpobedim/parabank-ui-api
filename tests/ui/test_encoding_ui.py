"""Кириллица и длина полей — дефекты, найденные на русских тестовых данных.

Страницы ParaBank отдаются в ISO-8859-1. Браузер отправляет из такой формы кириллицу
HTML-сущностями (&#1071;&#1085;), сервер сохраняет их как есть, а каждая буква превращается
в семь символов и быстро упирается в ограничение длины поля.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from parabank.api.client import ParaBankApi
from parabank.api.registration import RegisteredCustomer
from parabank.data.factories import FIELD_LIMITS, new_customer
from parabank.pages.auth_pages import RegisterPage
from parabank.pages.overview_page import OverviewPage

pytestmark = pytest.mark.ui

DEFECT_TIMEOUT_MS = 3_000


@pytest.fixture
def register_page(page: Page) -> RegisterPage:
    return RegisterPage(page).open().should_be_opened()


@pytest.mark.known_defect("PB-010", "кириллица из браузерной формы регистрации сохраняется HTML-сущностями")
def test_cyrillic_name_entered_in_browser_is_saved_as_text(
    register_page: RegisterPage, api: ParaBankApi
) -> None:
    # Короткое имя: даже в виде сущностей (14 символов) оно укладывается в лимит 30.
    profile = new_customer(latin=True, first_name="Ян")

    register_page.fill(profile)
    register_page.submit()

    expect(register_page.heading).to_have_text(f"Welcome {profile.username}")
    stored = api.login(profile.username, profile.password).first_name
    assert stored == "Ян", f"сохранено {stored!r}"


@pytest.mark.known_defect(
    "PB-011", "слишком длинное значение поля — ложная ошибка «This username already exists.»"
)
def test_overlong_city_gets_its_own_validation_message(register_page: RegisterPage) -> None:
    profile = new_customer(latin=True, city="C" * (FIELD_LIMITS["city"] + 1))

    register_page.fill(profile)
    register_page.submit()

    expect(register_page.error_for("customer.address.city")).to_be_visible(timeout=DEFECT_TIMEOUT_MS)
    expect(register_page.error_for("customer.username")).to_be_hidden()


@pytest.mark.known_defect("PB-012", "кириллица в приветствии личного кабинета выводится знаками «?»")
def test_cyrillic_name_is_shown_in_greeting(customer_page: Page, customer: RegisteredCustomer) -> None:
    # Клиент зарегистрирован через HTTP-форму в UTF-8: в базе имя хранится корректно.
    overview = OverviewPage(customer_page).open().should_be_opened()

    expect(overview.greeting).to_contain_text(customer.profile.first_name, timeout=DEFECT_TIMEOUT_MS)
