import os
import random
import re
import subprocess
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from enum import Enum

import typer
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

INTERSLEEP_TIME = 2
TIMENET_USERNAME = os.environ.get("AUTOPUNCH_TIMENET_USER", "_NO_USER_")
TIMENET_PASSWORD = os.environ.get("AUTOPUNCH_TIMENET_PASSWORD", "_NO_PASSWORD_")
GCP_PROJECT_ID = os.environ.get("AUTOPUNCH_GCP_PROJECT_ID", "_NO_GCP_PROJECT_ID_")
GCP_JOB_NAME = os.environ.get("AUTOPUNCH_GCP_JOB_NAME", "_NO_GCP_JOB_NAME_")
GCP_LOCATION = os.environ.get("AUTOPUNCH_GCP_LOCATION", "_NO_GCP_LOCATION_")

app = typer.Typer()


class Infra(str, Enum):
    at = "at"
    gcp = "gcp"


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
        user_input = driver.find_element(by=By.ID, value="user")
        user_input.send_keys(TIMENET_USERNAME)
        pass_input = driver.find_element(by=By.CSS_SELECTOR, value="#password input")
        pass_input.send_keys(TIMENET_PASSWORD)
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


@app.command()
def punch(dev: bool = False):
    "Enter timenet and punch in or out depending on the current state"
    with enter_timenet(headless=not dev) as driver:
        label = "Sortida" if am_i_working(driver) else "Entrada"
        driver.find_element(
            by=By.CSS_SELECTOR, value=f"button[aria-label={label}]"
        ).click()
        sleep()


def schedule_with_at(times, today, noise=0):
    "Schedule one-shot 'autopunch punch' runs for today via the local 'at' daemon"
    now = datetime.now()
    for hour in times:
        target = datetime(today.year, today.month, today.day, hour)
        if noise:
            target += timedelta(minutes=random.gauss(0, noise))
        if target <= now:
            typer.echo(
                f"Aviso: las {hour:02d}:00 ya han pasado, no se programa ese punch",
                err=True,
            )
            continue
        subprocess.run(
            ["at", target.strftime("%H:%M"), target.strftime("%m/%d/%Y")],
            input="autopunch punch\n",
            text=True,
            check=True,
        )


def schedule_with_gcp(times, today):
    "Reprogram the GCP Cloud Scheduler job to punch at today's computed times"
    from google.cloud import scheduler_v1
    from google.protobuf import field_mask_pb2

    client = scheduler_v1.CloudSchedulerClient()
    job = client.get_job(
        name=f"projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}/jobs/{GCP_JOB_NAME}"
    )
    cron_hours = ",".join(str(x) for x in times)
    job.schedule = f"0 {cron_hours} {today.day} {today.month} *"
    update_mask = field_mask_pb2.FieldMask(paths=["schedule"])
    client.update_job(job=job, update_mask=update_mask)


@app.command()
def program(infra: Infra = Infra.at, dev: bool = False, noise: int = 0):
    "Compute today's punch times and schedule them, locally via 'at' or in GCP"
    with enter_timenet(headless=not dev) as driver:
        today = date.today()
        total_expected_hours = extract_working_hours(driver, date=today)
        if total_expected_hours == 0:
            return
        if total_expected_hours <= 6:
            times = [9, 9 + total_expected_hours]
        else:
            times = [9, 13, 14, 14 + total_expected_hours - 4]
        if infra == Infra.at:
            schedule_with_at(times, today, noise=noise)
        else:
            if noise:
                typer.echo(
                    "Aviso: --noise no tiene efecto con --infra gcp", err=True
                )
            schedule_with_gcp(times, today)


if __name__ == "__main__":
    app()
