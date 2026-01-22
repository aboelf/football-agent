from playwright.sync_api import sync_playwright
import traceback

print('Checking Playwright and Chromium...')
try:
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
            print('Chromium launch: OK')
            browser.close()
        except Exception as e:
            print('Chromium launch: FAILED')
            print(e)
    print('Playwright import: OK')
except Exception as e:
    print('Playwright import: FAILED')
    traceback.print_exc()
