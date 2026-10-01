"""Регистрация клиента через HTTP-форму register.htm — без браузера.

REST API ParaBank не умеет создавать клиентов, а через UI регистрация занимает около 2 с.
Форма не требует CSRF-токена, поэтому POST с cookie сессии регистрирует клиента примерно
за 0,1 с. Сессия после регистрации уже авторизована: её cookie JSESSIONID можно передать
в браузер и начинать UI-тест сразу со страниц личного кабинета.

Одновременную запись ParaBank теряет (дефект PB-013), поэтому набор запускается последовательно.
"""

from __future__ import annotations

from dataclasses import dataclass

import allure
import requests

from parabank.api.client import ParaBankApi
from parabank.config import Settings
from parabank.data.factories import NewCustomer


class RegistrationError(Exception):
    pass


@dataclass(frozen=True)
class RegisteredCustomer:
    profile: NewCustomer
    customer_id: int
    session_id: str

    @property
    def username(self) -> str:
        return self.profile.username

    @property
    def password(self) -> str:
        return self.profile.password


def try_register(settings: Settings, customer: NewCustomer) -> str | None:
    """Одна отправка формы. Возвращает JSESSIONID авторизованной сессии или None,
    если ParaBank не показал приветствие (вернул форму с ошибкой или ответил 5xx)."""
    with requests.Session() as http:
        form_url = f"{settings.site_url}register.htm"
        http.get(form_url, timeout=settings.timeout).raise_for_status()
        response = http.post(form_url, data=customer.form_data(), timeout=settings.timeout)
        if response.ok and f"Welcome {customer.username}" in response.text:
            return http.cookies.get("JSESSIONID")
        return None


def register_customer(settings: Settings, api: ParaBankApi, customer: NewCustomer) -> RegisteredCustomer:
    with allure.step(f"Регистрация клиента {customer.username} через HTTP-форму"):
        session_id = try_register(settings, customer)
        if session_id is None:
            raise RegistrationError(f"ParaBank не зарегистрировал клиента {customer.username}")
    customer_id = api.login(customer.username, customer.password).id
    return RegisteredCustomer(profile=customer, customer_id=customer_id, session_id=session_id)
