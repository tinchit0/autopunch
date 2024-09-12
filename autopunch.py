import re
import time
from contextlib import contextmanager
from datetime import date

import click
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

INTERSLEEP_TIME = 2


def sleep():
    time.sleep(INTERSLEEP_TIME)


@contextmanager
def enter_timenet(headless=True):
    driver = None
    try:
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.set_preference("geo.enabled", False)
        options.set_preference("dom.webnotifications.enabled", False)
        driver = webdriver.Firefox(options=options)
        driver.get(
            "https://timenet.gpisoftware.com/wcp/login/f94ff22a-8361-4033-80ef-215feda7babe"
        )
        sleep()
        pin_input = driver.find_element(by=By.ID, value="gpi-input-0")
        pin_input.send_keys("xxxx")
        submit_button = driver.find_element(
            by=By.CSS_SELECTOR, value="button[aria-label=Entrar]"
        )
        submit_button.click()
        sleep()
        yield driver
    finally:
        if driver:
            driver.quit()


def extract_working_hours(driver, date=date.today()):
    day_number = date.day - 1
    week_number = date.isocalendar().week
    day_in_calendar = driver.find_element(
        by=By.CSS_SELECTOR,
        value=f'div[data-day="{day_number}"][data-week="{week_number}"]',
    )
    hover_day = ActionChains(driver).move_to_element(day_in_calendar)
    hover_day.perform()
    sleep()
    tooltip_id = day_in_calendar.get_attribute("aria-describedby")
    tooltip = driver.find_element(by=By.ID, value=tooltip_id)
    match = re.search(r"\((\d+)h\)", tooltip.text)
    working_hours = int(match.group(1))
    return working_hours


@click.command()
@click.argument("mode", type=click.Choice(["in", "out"], case_sensitive=False))
@click.option("--dev", is_flag=True, default=False, help="Dev mode")
def punch(mode, dev):
    with enter_timenet(headless=not dev) as driver:
        days_working_hours = extract_working_hours(driver)
        if days_working_hours == 0:
            return
        label = "Sortida" if mode == "out" else "Entrada"
        driver.find_element(
            by=By.CSS_SELECTOR, value=f"button[aria-label={label}]"
        ).click()
        sleep()


if __name__ == "__main__":
    punch()
