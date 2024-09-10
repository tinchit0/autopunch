import time
from datetime import date

import click
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from workalendar.europe import Catalonia

INTERSLEEP_TIME = 2


@click.group()
def cli():
    pass


def is_holiday():
    calendar = Catalonia()
    today = date.today()
    return calendar.is_holiday(today)


def enter_timenet():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.set_preference("geo.enabled", False)
    options.set_preference("dom.webnotifications.enabled", False)
    driver = webdriver.Firefox(options=options)
    driver.get(
        "https://timenet.gpisoftware.com/wcp/login/f94ff22a-8361-4033-80ef-215feda7babe"
    )
    time.sleep(INTERSLEEP_TIME)
    pin_input = driver.find_element(by=By.ID, value="gpi-input-0")
    pin_input.send_keys("xxxx")
    submit_button = driver.find_element(
        by=By.CSS_SELECTOR, value="button[aria-label=Entrar]"
    )
    submit_button.click()
    return driver


@cli.command()
@click.option(
    "--check-holiday", is_flag=True, default=False, help="Abort if it's holiday"
)
def punch_in(check_holiday):
    if check_holiday and is_holiday():
        return
    driver = enter_timenet()
    time.sleep(INTERSLEEP_TIME)
    enter_button = driver.find_element(
        by=By.CSS_SELECTOR, value="button[aria-label=Entrada]"
    )
    enter_button.click()
    time.sleep(INTERSLEEP_TIME)
    driver.quit()


@cli.command()
@click.option(
    "--check-holiday", is_flag=True, default=False, help="Abort if it's holiday"
)
def punch_out(check_holiday):
    if check_holiday and is_holiday():
        return
    driver = enter_timenet()
    time.sleep(INTERSLEEP_TIME)
    exit_button = driver.find_element(
        by=By.CSS_SELECTOR, value="button[aria-label=Sortida]"
    )
    exit_button.click()
    time.sleep(INTERSLEEP_TIME)
    driver.quit()


if __name__ == "__main__":
    cli()
