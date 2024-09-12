import re
import time
from contextlib import contextmanager
from datetime import date

import click
from google.cloud import scheduler_v1
from google.protobuf import field_mask_pb2
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


def am_i_working(driver):
    state_label = driver.find_element(
        by=By.CSS_SELECTOR, value="div.container-time div.text"
    )
    return state_label.text in ("trabajando", "acabas de entrar")


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


@click.group()
def cli():
    pass


@cli.command()
@click.option("--dev", is_flag=True, default=False, help="Dev mode")
def punch(dev):
    with enter_timenet(headless=not dev) as driver:
        label = "Sortida" if am_i_working(driver) else "Entrada"
        driver.find_element(
            by=By.CSS_SELECTOR, value=f"button[aria-label={label}]"
        ).click()
        sleep()


@cli.command()
@click.option("--dev", is_flag=True, default=False, help="Dev mode")
def program(dev):
    with enter_timenet(headless=not dev) as driver:
        today = date.today()
        total_expected_hours = extract_working_hours(driver, date=today)
        if total_expected_hours == 0:
            return
        client = scheduler_v1.CloudSchedulerClient()
        project_id = "endless-anagram-324913"
        job_name = "autopunch-scheduler-trigger"
        location = "us-central1"
        job = client.get_job(
            name=f"projects/{project_id}/locations/{location}/jobs/{job_name}"
        )
        if total_expected_hours <= 6:
            times = [9, 9 + total_expected_hours]
        else:
            times = [9, 13, 14, 14 + total_expected_hours - 4]
        cron_hours = ",".join(str(x) for x in times)
        job.schedule = f"0 {cron_hours} {today.day} {today.month} *"
        update_mask = field_mask_pb2.FieldMask(paths=["schedule"])
        client.update_job(job=job, update_mask=update_mask)


if __name__ == "__main__":
    cli()
