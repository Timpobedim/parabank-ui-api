"""Вход и регистрация."""

from __future__ import annotations

from typing import Self

import allure
from playwright.sync_api import Locator, Page, expect

from parabank.data.factories import NewCustomer
from parabank.pages.base_page import BasePage
from parabank.pages.overview_page import OverviewPage


class HomePage:
    path = "index.htm"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.username = page.locator("#loginPanel input[name='username']")
        self.password = page.locator("#loginPanel input[name='password']")
        self.login_button = page.locator("#loginPanel input[value='Log In']")
        self.error = page.locator("#rightPanel .error")

    def open(self) -> Self:
        self.page.goto(self.path)
        return self

    def should_be_opened(self) -> Self:
        expect(self.login_button).to_be_visible()
        return self

    def submit(self, username: str, password: str) -> None:
        with allure.step(f"UI: вход как «{username}»"):
            self.username.fill(username)
            self.password.fill(password)
            self.login_button.click()

    def login(self, username: str, password: str) -> OverviewPage:
        self.submit(username, password)
        return OverviewPage(self.page)


class RegisterPage(BasePage):
    path = "register.htm"
    title = "Signing up is easy!"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.register_button = page.locator("input[value='Register']")
        self.success_text = page.get_by_text("Your account was created successfully. You are now logged in.")

    def field(self, field_id: str) -> Locator:
        # id вида customer.firstName: точка в CSS-селекторе #id означала бы класс.
        return self.page.locator(f"[id='{field_id}']")

    def error_for(self, field_id: str) -> Locator:
        return self.page.locator(f"[id='{field_id}.errors']")

    def fill(self, customer: NewCustomer, repeated_password: str | None = None) -> None:
        with allure.step(f"UI: заполнение формы регистрации для {customer.username}"):
            for field_id, value in customer.form_data(repeated_password).items():
                self.field(field_id).fill(value)

    def submit(self) -> None:
        self.register_button.click()
