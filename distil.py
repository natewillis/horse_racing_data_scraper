import pychrome
import base64
import time
import os
import subprocess
from fake_useragent import UserAgent


def spoofing_scripts():

    return [
    """
    (() => {
    Object.defineProperty(navigator, 'webdriver', {
      get: () => false,
    });
    })()
    """,
    """
    (() => {
    // We can mock this in as much depth as we need for the test.
    window.navigator.chrome = {
      runtime: {},
      // etc.
    };
    })()
    """,
    """
    (() => {
    const originalQuery = window.navigator.permissions.query;
    return window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );
    })()
    """,
    """
    (() => {
    // Overwrite the `plugins` property to use a custom getter.
    Object.defineProperty(navigator, 'plugins', {
      // This just needs to have `length > 0` for the current test,
      // but we could mock the plugins too if necessary.
      get: () => [1, 2, 3, 4, 5],
    });
    })()
    """,
    """
    (() => {
    // Overwrite the `languages` property to use a custom getter.
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
    });
    })()
    """
    ]


def bypass_distil_get_html(url):

    # Figure out which system we're on
    windows_chrome_path = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
    centos_chrome_path = 'google-chrome'
    chrome_path = ''
    if os.path.exists(windows_chrome_path):
        chrome_path = windows_chrome_path
    else:
        chrome_path = centos_chrome_path

    # Create instance of chrome for scraping
    process = subprocess.Popen([chrome_path, "--headless", "--disable-gpu", "--remote-debugging-port=9222"])
    time.sleep(5)  # Give it a few seconds to startup

    # Connect to chrome
    browser = pychrome.Browser(url="http://127.0.0.1:9222")

    # Create a random useragent for browsing
    ua = UserAgent()
    user_agent = ua.random

    # Create a tab for browsing
    tab = browser.new_tab()
    tab.start()
    tab.call_method("Network.enable")
    tab.call_method("Page.enable")
    tab.call_method("Network.setUserAgentOverride", userAgent=user_agent)

    # Get spoofing scripts
    scripts = spoofing_scripts()

    # Adding scripts to this tab
    for s in scripts:
        tab.call_method("Page.addScriptToEvaluateOnNewDocument", source=s)

    # Load page
    tab.call_method("Page.navigate", url=url, _timeout=5)

    # Wait for loading TODO: figure out a more reliable method for this
    tab.wait(10)

    # Grab source
    response_json = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
    html = response_json['result']['value']

    # Stop the tab
    tab.stop()

    # Close tab
    browser.close_tab(tab)

    # Close chrome
    process.terminate()

    # Return
    return html