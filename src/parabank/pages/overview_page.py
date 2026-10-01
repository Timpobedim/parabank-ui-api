from __future__ import annotations

from playwright.sync_api import Locator, Page

from parabank.pages.base_page import BasePage


class OverviewPage(BasePage):
    """Обзор счетов. Таблица заполняется запросом к REST API уже после загрузки страницы."""

    path = "overview.htm"
    title = "Accounts Overview"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.table = page.locator("#accountTable")
        self.rows = self.table.locator("tbody tr")
        # «Welcome <имя> <фамилия>» над меню — единственное место, где страница выводит имя сервером.
        self.greeting = page.locator("#leftPanel .smallText")

    def account_link(self, account_id: int) -> Locator:
        return self.table.get_by_role("link", name=str(account_id), exact=True)

    def balance_of(self, account_id: int) -> Locator:
        # Локатор внутри filter(has=…) ищется относительно строки, поэтому он строится от page,
        # а не от таблицы: «#accountTable >> link» внутри строки не нашёлся бы никогда.
        link = self.page.get_by_role("link", name=str(account_id), exact=True)
        return self.rows.filter(has=link).locator("td").nth(1)
