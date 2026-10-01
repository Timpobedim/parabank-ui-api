"""Фикстуры: настройки стенда, API-клиент, свежий клиент банка на каждый тест, вход в UI по cookie."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlsplit

import allure
import pytest
import requests
from playwright.sync_api import Page

from parabank.api.client import ParaBankApi
from parabank.api.models import Account
from parabank.api.registration import RegisteredCustomer, register_customer
from parabank.config import Settings, get_settings
from parabank.data.factories import new_customer

STAND_STARTUP_SECONDS = 120


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def _stand_is_up(settings: Settings) -> None:
    """Контейнер ParaBank поднимается 20–40 с. Ждём ответа стенда один раз, а не роняем первые тесты."""
    deadline = time.monotonic() + STAND_STARTUP_SECONDS
    while True:
        try:
            if requests.get(f"{settings.site_url}index.htm", timeout=5).ok:
                return
        except requests.RequestException:
            pass
        if time.monotonic() > deadline:
            pytest.exit(f"ParaBank не отвечает: {settings.base_url}", returncode=3)
        time.sleep(2)


@pytest.fixture(scope="session")
def api(settings: Settings) -> Iterator[ParaBankApi]:
    client = ParaBankApi(settings.api_url, settings.timeout)
    yield client
    client.close()


@pytest.fixture
def customer(settings: Settings, api: ParaBankApi) -> RegisteredCustomer:
    return register_customer(settings, api, new_customer())


@pytest.fixture
def checking_account(api: ParaBankApi, customer: RegisteredCustomer) -> Account:
    """Единственный счёт нового клиента: CHECKING с приветственными $515.50."""
    [account] = api.get_accounts(customer.customer_id)
    return account


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], settings: Settings) -> dict[str, Any]:
    return {**browser_context_args, "base_url": settings.site_url}


@pytest.fixture
def customer_page(page: Page, customer: RegisteredCustomer, settings: Settings) -> Page:
    """Браузер с уже авторизованной сессией клиента: форма входа проверяется отдельными тестами."""
    url = urlsplit(settings.base_url)
    page.context.add_cookies(
        [{"name": "JSESSIONID", "value": customer.session_id, "domain": url.hostname or "", "path": url.path}]
    )
    return page


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """known_defect("PB-001", "…") → xfail(strict=True, raises=AssertionError).

    Пока дефект есть, тест «ожидаемо падает»; исправят — станет XPASS и прогон покраснеет.
    raises=AssertionError: за дефект принимается только провал проверки, а не ошибка окружения.
    """
    for item in items:
        marker = item.get_closest_marker("known_defect")
        if marker is not None:
            bug_id, summary = marker.args
            bug_report = f"docs/bug-reports/{bug_id}.md"
            item.add_marker(
                pytest.mark.xfail(
                    reason=f"{bug_id}: {summary} ({bug_report})", strict=True, raises=AssertionError
                )
            )
            # В отчёте Allure у теста появляется ссылка-issue на баг-репорт.
            item.add_marker(pytest.mark.allure_link(bug_report, link_type="issue", name=bug_id))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Iterator[None]:
    """Скриншот страницы в отчёт Allure, если UI-тест упал."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = getattr(item, "funcargs", {}).get("page")
        if page is not None and not page.is_closed():
            screenshot = page.screenshot(full_page=True)
            allure.attach(screenshot, name="скриншот", attachment_type=allure.attachment_type.PNG)
