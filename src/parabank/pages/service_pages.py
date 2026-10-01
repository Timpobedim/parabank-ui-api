"""Оплата счетов и контактные данные."""

from __future__ import annotations

from decimal import Decimal

import allure
from playwright.sync_api import Locator, Page, expect

from parabank.api.models import Payee
from parabank.pages.base_page import BasePage


class BillPayPage(BasePage):
    path = "billpay.htm"
    title = "Bill Payment Service"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.from_select = page.locator("#billpayForm select[name='fromAccountId']")
        self.send_button = page.locator("input[value='Send Payment']")
        self.visible_errors = page.locator("#billpayForm span.error:visible")
        self.result_heading = page.locator("#billpayResult h1")
        self.result_text = page.locator("#billpayResult p").first

    def input(self, name: str) -> Locator:
        return self.page.locator(f"#billpayForm input[name='{name}']")

    def fill(
        self, payee: Payee, amount: Decimal, from_account_id: int, verify_account: int | None = None
    ) -> None:
        with allure.step(f"UI: платёж {amount} получателю «{payee.name}»"):
            values = {
                "payee.name": payee.name,
                "payee.address.street": payee.address.street,
                "payee.address.city": payee.address.city,
                "payee.address.state": payee.address.state,
                "payee.address.zipCode": payee.address.zip_code,
                "payee.phoneNumber": payee.phone_number,
                "payee.accountNumber": str(payee.account_number),
                "verifyAccount": str(payee.account_number if verify_account is None else verify_account),
                "amount": str(amount),
            }
            for name, value in values.items():
                self.input(name).fill(value)
            self.from_select.select_option(str(from_account_id))

    def send(self) -> None:
        self.send_button.click()


class UpdateProfilePage(BasePage):
    path = "updateprofile.htm"
    title = "Update Profile"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.update_button = page.locator("input[value='Update Profile']")
        self.result_heading = page.locator("#updateProfileResult h1")

    def field(self, field_id: str) -> Locator:
        return self.page.locator(f"[id='{field_id}']")

    def update(self, values: dict[str, str]) -> None:
        """values — {id поля: новое значение}, например {"customer.address.city": "Самара"}."""
        with allure.step(f"UI: обновление профиля {sorted(values)}"):
            # Форма заполняется текущими данными скриптом — ждём, иначе он затрёт наш ввод.
            expect(self.field("customer.firstName")).not_to_have_value("")
            for field_id, value in values.items():
                self.field(field_id).fill(value)
            self.update_button.click()
