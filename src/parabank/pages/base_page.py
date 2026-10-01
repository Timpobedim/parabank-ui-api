from __future__ import annotations

import re
from typing import ClassVar, Self

from playwright.sync_api import Locator, Page, expect


class AccountServicesMenu:
    """Меню «Account Services» в левой колонке — есть на всех страницах личного кабинета."""

    def __init__(self, page: Page) -> None:
        self._panel = page.locator("#leftPanel")

    def link(self, name: str) -> Locator:
        return self._panel.get_by_role("link", name=name, exact=True)

    def logout(self) -> None:
        self.link("Log Out").click()


class BasePage:
    """Страница личного кабинета. Пути относительные: base_url стенда заканчивается на /parabank/."""

    path: ClassVar[str]
    title: ClassVar[str]

    def __init__(self, page: Page) -> None:
        self.page = page
        self.menu = AccountServicesMenu(page)
        # На многих страницах в DOM лежат скрытые блоки ошибки со своим h1 — берём видимый.
        self.heading = page.locator("#rightPanel h1:visible").first

    def open(self) -> Self:
        self.page.goto(self.path)
        return self

    def should_be_opened(self) -> Self:
        # Tomcat может дописать к адресу ;jsessionid=…, поэтому ищем путь внутри URL.
        expect(self.page).to_have_url(re.compile(re.escape(self.path)))
        expect(self.heading).to_have_text(self.title)
        return self
