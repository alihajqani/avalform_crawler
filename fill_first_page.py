# fill_first_page.py

import json
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# If SITE_URL and PLAYWRIGHT_HEADLESS are defined in config.py, import them:
# from config import SITE_URL, PLAYWRIGHT_HEADLESS

SITE_URL = "https://form.avalform.com/view.php?id=70833985"  # URL of page 1
PLAYWRIGHT_HEADLESS = False  # Set True for headless mode

DATA_FILE = Path("persons.json")


def fill_first_page(person_data: dict, page) -> None:
    """
    Fill page 1 fields (element_2, element_3, element_4, element_5, element_6),
    then click 'Continue'.
    """
    for field_name, value in person_data.items():
        selector_input = f'input[name="{field_name}"], input#{field_name}'
        try:
            if page.query_selector(selector_input):
                page.fill(selector_input, str(value))
                continue

            selector_select = f'select[name="{field_name}"], select#{field_name}'
            if page.query_selector(selector_select):
                page.select_option(selector_select, str(value))
                continue

            print(f"[WARNING] No input/select found for '{field_name}'.")
        except Exception as e:
            print(f"[ERROR] Filling '{field_name}' with '{value}' failed: {e}")

    try:
        page.click("input#submit_primary", timeout=5000)  # Click 'ادامه' on page 1
    except PlaywrightTimeoutError:
        print("[ERROR] Could not find/click 'Continue' on page 1.")


def fill_radio_matrix_page(page, timeout=5000) -> None:
    """
    Helper for pages that present a radio‐button matrix (pages 2–4, 6, 8).
    Wait until any <input type='radio'> appears, group by 'name', pick one random
    value from that group's actual values, and check it.
    """
    try:
        page.wait_for_selector('input[type="radio"]', timeout=timeout)
    except PlaywrightTimeoutError:
        return  # No radios here

    radio_elements = page.query_selector_all('input[type="radio"]')
    groups = {}  # name → set of available values

    for elem in radio_elements:
        name_attr = elem.get_attribute("name")
        value_attr = elem.get_attribute("value")
        if not name_attr or not value_attr:
            continue
        groups.setdefault(name_attr, set()).add(value_attr)

    for name, value_set in groups.items():
        chosen_value = random.choice(list(value_set))
        selector = f'input[name="{name}"][value="{chosen_value}"]'
        try:
            if page.query_selector(selector):
                page.check(selector)
            else:
                print(f"[WARNING] For group '{name}', value={chosen_value} not found.")
        except Exception as e:
            print(f"[ERROR] Checking '{selector}' failed: {e}")


def click_continue(page) -> None:
    """
    Click the 'Continue' button (id=submit_primary) on the current page.
    """
    try:
        page.click("input#submit_primary", timeout=5000)
    except PlaywrightTimeoutError:
        print("[ERROR] Could not find/click 'Continue' (or 'ارسال') on this page.")


def fill_page_5_or_7(page) -> None:
    """
    Pages 5 and 7 use multiple_choice blocks where <label> intercepts the click
    on <input>. Click the <label> for a randomly chosen radio (value and id) instead.
    """
    try:
        page.wait_for_selector('input[type="radio"]', timeout=5000)
    except PlaywrightTimeoutError:
        return

    radio_elements = page.query_selector_all('input[type="radio"]')
    groups = {}  # name → list of (value, id)

    for elem in radio_elements:
        name_attr = elem.get_attribute("name")
        value_attr = elem.get_attribute("value")
        id_attr = elem.get_attribute("id")
        if not name_attr or not value_attr or not id_attr:
            continue
        groups.setdefault(name_attr, []).append((value_attr, id_attr))

    for name, options in groups.items():
        chosen_value, chosen_id = random.choice(options)
        label_selector = f'label[for="{chosen_id}"]'
        try:
            if page.query_selector(label_selector):
                page.click(label_selector, timeout=5000)
            else:
                print(f"[WARNING] Label for id '{chosen_id}' not found.")
        except Exception as e:
            print(f"[ERROR] Clicking label '{label_selector}' failed: {e}")


def main():
    if not DATA_FILE.exists():
        print(f"[ERROR] '{DATA_FILE}' not found.")
        return

    people = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
        page = browser.new_page()

        for idx, person in enumerate(people, start=1):
            print(f"\n=== Processing person #{idx} ===")

            # --- Page 1 ---
            try:
                page.goto(SITE_URL, timeout=30000)
            except PlaywrightTimeoutError:
                print("[ERROR] Could not load page 1. Check SITE_URL.")
                browser.close()
                return

            try:
                page.wait_for_selector("#form_container", timeout=10000)
            except PlaywrightTimeoutError:
                print("[ERROR] '#form_container' not found on page 1.")
                browser.close()
                return

            fill_first_page(person, page)
            # Wait for navigation to page 2
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 2 (matrix 1–6) ---
            fill_radio_matrix_page(page)
            click_continue(page)
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 3 (matrix 1–5) ---
            fill_radio_matrix_page(page)
            click_continue(page)
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 4 (matrix 1–5) ---
            fill_radio_matrix_page(page)
            click_continue(page)
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 5 (multiple_choice) ---
            fill_page_5_or_7(page)
            click_continue(page)
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 6 (matrix 1–5) ---
            fill_radio_matrix_page(page)
            click_continue(page)
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 7 (multiple_choice) ---
            fill_page_5_or_7(page)
            click_continue(page)
            try:
                page.wait_for_timeout(1000)
            except:
                pass

            # --- Page 8 (two matrix blocks: first 1–2, second 1–5) ---
            fill_radio_matrix_page(page)
            click_continue(page)
            # After this click, form is 'ارسال'ed

            print(f"=== Person #{idx} done. ===")
            # Uncomment to pause between records:
            # input("Press Enter for next person...")

        input("All done. Press Enter to close the browser...")
        print("Closing browser...")
        browser.close()


if __name__ == "__main__":
    main()
