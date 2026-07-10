import os
import random
import re
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

import typer
from loguru import logger
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


def configure_logging(logfile: Optional[str]):
    "Set up loguru sinks: always stderr, plus an optional logfile"
    logger.remove()
    logger.add(sys.stderr, level="INFO", diagnose=False)
    if logfile:
        logger.add(logfile, level="INFO", diagnose=False, rotation="10 MB", retention="30 days")


def sleep():
    time.sleep(INTERSLEEP_TIME)


@contextmanager
def enter_timenet(headless=True):
    driver = None
    try:
        logger.info("Arrancando Firefox (headless={})", headless)
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
        logger.info("Haciendo login en timenet como {}", TIMENET_USERNAME)
        user_input = driver.find_element(by=By.ID, value="user")
        user_input.send_keys(TIMENET_USERNAME)
        pass_input = driver.find_element(by=By.CSS_SELECTOR, value="#password input")
        pass_input.send_keys(TIMENET_PASSWORD)
        submit_button = driver.find_element(
            by=By.CSS_SELECTOR, value="button[aria-label=Entrar]"
        )
        submit_button.click()
        sleep()
        logger.info("Login en timenet completado")
        yield driver
    finally:
        if driver:
            driver.quit()
            logger.debug("Firefox cerrado")


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
def punch(
    dev: bool = False,
    logfile: Optional[str] = typer.Option(
        None, "--logfile", help="Fichero donde escribir los logs, además de stderr"
    ),
):
    "Enter timenet and punch in or out depending on the current state"
    configure_logging(logfile)
    try:
        with enter_timenet(headless=not dev) as driver:
            label = "Sortida" if am_i_working(driver) else "Entrada"
            logger.info("Estado detectado, se pulsará el botón '{}'", label)
            driver.find_element(
                by=By.CSS_SELECTOR, value=f"button[aria-label={label}]"
            ).click()
            sleep()
        logger.success("Punch completado ({})", label)
    except Exception:
        logger.exception("Fallo al hacer punch")
        raise


def schedule_with_at(times, today, noise=0, logfile=None):
    "Schedule one-shot 'autopunch punch' runs for today via the local 'at' daemon"
    now = datetime.now()
    for hour in times:
        target = datetime(today.year, today.month, today.day, hour)
        if noise:
            target += timedelta(minutes=random.gauss(0, noise))
        if target <= now:
            logger.warning(
                "Las {:02d}:00 ya han pasado, no se programa ese punch", hour
            )
            continue
        punch_cmd = "autopunch punch"
        if logfile:
            punch_cmd += f" --logfile {shlex.quote(logfile)}"
        logger.info(
            "Programando '{}' a las {} vía 'at'",
            punch_cmd,
            target.strftime("%H:%M %m/%d/%Y"),
        )
        subprocess.run(
            ["at", target.strftime("%H:%M"), target.strftime("%m/%d/%Y")],
            input=f"{punch_cmd}\n",
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
    logger.info("Cloud Scheduler job actualizado con schedule '{}'", job.schedule)


@app.command()
def program(
    infra: Infra = Infra.at,
    dev: bool = False,
    noise: int = 0,
    logfile: Optional[str] = typer.Option(
        None,
        "--logfile",
        help="Fichero donde escribir los logs; se propaga a los 'punch' programados vía 'at'",
    ),
):
    "Compute today's punch times and schedule them, locally via 'at' or in GCP"
    configure_logging(logfile)
    try:
        with enter_timenet(headless=not dev) as driver:
            today = date.today()
            total_expected_hours = extract_working_hours(driver, date=today)
            logger.info("Horas esperadas hoy: {}", total_expected_hours)
            if total_expected_hours == 0:
                logger.info("0 horas esperadas, no se programa ningún punch")
                return
            if total_expected_hours <= 6:
                times = [9, 9 + total_expected_hours]
            else:
                times = [9, 13, 14, 14 + total_expected_hours - 4]
            logger.info("Horas de punch calculadas: {}", times)
            if infra == Infra.at:
                schedule_with_at(times, today, noise=noise, logfile=logfile)
            else:
                if noise:
                    logger.warning("--noise no tiene efecto con --infra gcp")
                schedule_with_gcp(times, today)
    except Exception:
        logger.exception("Fallo en program")
        raise


if __name__ == "__main__":
    app()
