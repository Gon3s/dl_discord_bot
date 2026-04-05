"""
Génère les screenshots de démo pour le README GitHub.
Usage : cd backend && uv run python ../demo/capture.py
"""

import time
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

BASE = "http://localhost:8000"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)

W, H = 1400, 860


def shot(driver, name: str):
    path = str(OUT / f"{name}.png")
    driver.save_screenshot(path)
    print(f"  ✓ {name}.png")


def wait_for(driver, css: str, timeout: int = 20):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )


def do_search(driver, query: str, category: str = "films"):
    driver.get(f"{BASE}/search")
    wait_for(driver, 'input[placeholder="SEARCH…"]')
    time.sleep(0.8)

    # Sélectionner la catégorie
    btns = driver.find_elements(By.CSS_SELECTOR, "button.font-black")
    for btn in btns:
        if btn.text.strip().upper() == category.upper():
            btn.click()
            break
    time.sleep(0.3)

    # Taper la recherche
    inp = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="SEARCH…"]')
    inp.clear()
    inp.send_keys(query)
    inp.send_keys(Keys.RETURN)

    wait_for(driver, ".result-card", timeout=20)
    time.sleep(1.5)


driver = Driver(browser="chrome", headless=True)
driver.set_window_size(W, H)

try:
    # ── 1. Search — page vide ───────────────────────────────────────────────
    print("1. Search (vide)…")
    driver.get(f"{BASE}/search")
    wait_for(driver, 'input[placeholder="SEARCH…"]')
    time.sleep(1.5)
    shot(driver, "01_search_empty")

    # ── 2. Search — résultats films ─────────────────────────────────────────
    print("2. Search résultats films…")
    do_search(driver, "young sherlock", "films")
    shot(driver, "02_search_results")

    # ── 3. Modal download ───────────────────────────────────────────────────
    print("3. Modal download…")
    driver.find_element(By.CSS_SELECTOR, ".result-card").click()
    time.sleep(1.5)
    shot(driver, "03_download_modal")
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    time.sleep(0.5)

    # ── 4. Search séries + badge DL ─────────────────────────────────────────
    print("4. Search séries…")
    do_search(driver, "young sherlock", "series")
    shot(driver, "04_search_series")

    # ── 5. Panel épisodes ───────────────────────────────────────────────────
    print("5. Panel épisodes…")
    driver.find_element(By.CSS_SELECTOR, ".result-card").click()
    wait_for(driver, ".ep-row", timeout=20)
    time.sleep(2)
    shot(driver, "05_episodes_panel")
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    time.sleep(0.5)

    # ── 6. Downloads ────────────────────────────────────────────────────────
    print("6. Downloads…")
    driver.get(f"{BASE}/downloads")
    time.sleep(2)
    shot(driver, "06_downloads")

    # ── 7. History ──────────────────────────────────────────────────────────
    print("7. History…")
    driver.get(f"{BASE}/history")
    time.sleep(2)
    shot(driver, "07_history")

    # ── 8. Settings ─────────────────────────────────────────────────────────
    print("8. Settings…")
    driver.get(f"{BASE}/settings")
    time.sleep(2)
    shot(driver, "08_settings")

finally:
    driver.quit()

screenshots = sorted(OUT.glob("*.png"))
print(f"\nDone — {len(screenshots)} screenshots dans demo/screenshots/")
for p in screenshots:
    print(f"  {p.name}")
