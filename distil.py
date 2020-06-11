import asyncio
from pyppeteer import launch
from pyppeteer.errors import TimeoutError, PageError
from pyppeteer_stealth import stealth
import time
import os
import datetime
from settings import CAPTCHA_STORAGE_PATH, TOR_CONTROL_PASSWORD, EQUIBASE_PDF_PATH
import cv2
import numpy as np
import random
from stem import Signal
from stem.control import Controller
import glob


def reconnect_tor():

    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password=TOR_CONTROL_PASSWORD)
        print('authentication success')
        controller.signal(Signal.NEWNYM)
        print('new tor connection processed')


def solve_geetest_captcha(image_path, final_image_path):

    # Find Puzzle Piece
    img = cv2.imread(image_path)
    img_shape = img.shape
    img_height = img_shape[0]
    img_width = img_shape[1]
    puzzle_width = 55

    # Crop it out
    puzzle_part = img[0:img_height, 0:puzzle_width]

    # Find puzzle piece contour
    imghsv = cv2.cvtColor(puzzle_part, cv2.COLOR_BGR2HSV)
    lower_yellow = np.array([25, 47, 0])
    upper_yellow = np.array([33, 237, 255])
    mask_yellow = cv2.inRange(imghsv, lower_yellow, upper_yellow)
    contours, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Get Bounding Rectangle
    if len(contours) == 0:
        print('this captcha cant be solved for some reason')
        return random.randrange(20, 80)
    areas = [cv2.contourArea(c) for c in contours]
    max_index = np.argmax(areas)
    cnt = contours[max_index]
    x, y, w, h = cv2.boundingRect(cnt)

    # Adjust bounding rectangle to include a little border
    border_width = 2
    x = max(x - border_width, 0)
    y = max(y - border_width, 0)
    w = w + (border_width * 2)
    h = h + (border_width * 2)

    # Primary template acquisition method - use contour bounding box combined with canny edge detection of raw image
    # Get just the puzzle piece
    puzzle_piece_img = puzzle_part[y:y+h, x:x+w]

    # Get edges of the puzzle piece
    median_puzzle = np.median(puzzle_piece_img)
    sigma = 0.33
    lower_edge_threshold = int(max(0, (1.0 - sigma) * median_puzzle))
    upper_edge_threshold = int(max(0, (1.0 - sigma) * median_puzzle))
    puzzle_piece_edges_canny = cv2.Canny(puzzle_piece_img, lower_edge_threshold, upper_edge_threshold)

    # Alternate template acquisition method - just use the contours themselves as the template
    # Get the contour image
    mask = np.ones(puzzle_part.shape[:2], dtype="uint8") * 255
    cv2.drawContours(mask, contours, -1, 0, -1)

    # Edge Detection of contour mask
    edges = cv2.Canny(mask, 100, 200)

    # Cut out the edges
    puzzle_piece_edges_contour = edges[y:y + h, x:x + w]

    # Crop out the rest of the image to search for edges in
    search_part = img[y:y + h, puzzle_width + 1:img_width]

    # Convert big image to grayscale
    gray = cv2.cvtColor(search_part, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    rest_of_image_edges = cv2.Canny(blurred, 10, 200)

    # Matching
    result = cv2.matchTemplate(rest_of_image_edges, puzzle_piece_edges_canny, cv2.TM_CCOEFF)
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    (startX, startY) = (maxLoc[0] + puzzle_width, maxLoc[1] + y)
    (endX, endY) = (startX + w, startY + h)

    cv2.rectangle(img, (startX, startY), (endX, endY), (0, 0, 255), 2)
    cv2.drawContours(img, contours, -1, (0, 0, 255), 1)
    cv2.imwrite(final_image_path, img)

    # Final Amount to move
    mouse_move_amount = startX - x
    print(f'Move the mouse {mouse_move_amount} pixels to the right')
    return mouse_move_amount


async def async_initialize_stealth_browser():

    # Set flag
    try_again_flag = False
    tor_connection_attempts = 0
    max_tor_connection_attempts = 3

    # Launch Browser
    browser = await launch({'args': ['--proxy-server=socks5://127.0.0.1:9050']})

    # Get incognito context
    context = await browser.createIncognitoBrowserContext()

    # Open a new page in the browser
    page = await context.newPage()

    # Stealth the browser window
    await stealth(page)

    # Check for tor
    try:
        await page.goto('https://check.torproject.org/')
    except PageError:
        print('Tor browser configuration failed')
        try_again_flag = True

    while try_again_flag and tor_connection_attempts < max_tor_connection_attempts:

        # Increment connection attempts
        tor_connection_attempts += 1
        print(f'attempting to reconnect tor ({tor_connection_attempts})')
        reconnect_tor()
        try:
            page.goto('https://check.torproject.org/')
            try_again_flag = False
        except PageError:
            print('Tor browser configuration failed AGAIN')
            try_again_flag = True
        except TimeoutError:
            print('Tor browser configuration failed AGAIN')
            try_again_flag = True

    if try_again_flag:
        raise Exception("Tor couldn't reach the test site to confirm it was running")

    # Get tor text
    tor_h1 = await page.querySelector('h1')

    if tor_h1 is not None:
        tor_h1_text = await page.evaluate('(element) => element.textContent', tor_h1)
        print(f'The tor text is {tor_h1_text.strip()}')
        if 'Congratulations' in tor_h1_text:
            print('Tor is configured!')
        else:
            print('Tor is not configured :(')
            raise Exception("Tor isnt configured for your browser!")
    else:
        print('wtf tor')
        html = await page.evaluate('document.body.innerHTML', force_expr=True)
        print(html)
        raise Exception("Tor isnt configured for your browser! Also its weird!")

    # Close Page
    await page.close()

    # Return browser
    return context


async def async_shutdown_stealth_browser(context):

    # Shutdown the browser
    browser = context.browser
    await context.close()
    await browser.close()


async def async_html_scrape_with_captcha(browser, url, loaded_selector):
    # Set captcha loop variables
    stealth_flag = True
    captcha_flag = True
    max_iterations = 3
    current_iterations = 0

    # Open the captcha loop
    while captcha_flag and current_iterations <= max_iterations:

        # Increase iterations
        current_iterations += 1

        # Open a new page in the browser
        page = await browser.newPage()

        # Stealth the browser window
        if stealth_flag:
            await stealth(page)

        # Navigate to url
        print(f'going to {url}')
        try:
            await page.goto(url)
        except TimeoutError:
            print('page timed out entirely, trying to recconect tor')
            reconnect_tor()
            await page.close()
            continue
        except PageError:
            print('something went wrong with the connection, lets try again')
            reconnect_tor()
            await page.close()
            continue

        # Test for distil rejection
        try:
            await page.waitForSelector('#distilIdentificationBlock', {'timeout': 5000})
            print('Distil discovered our stealth! Unhide!')
            stealth_flag = False
            time.sleep(5)
            await page.close()
            continue
        except TimeoutError:
            pass

        # Test for captcha
        try:
            await page.waitForSelector('#distilCaptchaForm', {'timeout': 10000})
            print('Theres a captcha!')
            captcha_flag = True
        except TimeoutError:
            print('no captcha!')
            captcha_flag = False

        # Process captcha if necessary
        if captcha_flag:

            # Captcha time
            captcha_time = datetime.datetime.now()

            # Click to verify
            time.sleep(5)
            try:
                verify_button = await page.waitForSelector('div.geetest_holder', {'timeout': 30000})
            except TimeoutError:
                print('The captcha changed or laoding is broken or something. Reconnecting tor and exiting.')
                reconnect_tor()
                await page.close()
                return ''

            await verify_button.click({'button': 'left', 'clickCount': 1, 'delay': 10})

            # Wait for captcha to load
            await page.waitForSelector('canvas.geetest_canvas_slice.geetest_absolute', {'visible': True})

            # Sleep so the fade in goes away
            time.sleep(2)

            # Get the captcha image
            await page.waitForSelector('canvas.geetest_canvas_bg.geetest_absolute', {'visible': True})
            bg = await page.querySelector('canvas.geetest_canvas_bg.geetest_absolute')
            unsolved_captcha_path = os.path.join(
                CAPTCHA_STORAGE_PATH,
                captcha_time.strftime('%Y%m%d-%H%M%S') + '-unsolved.png'
            )
            await bg.screenshot({'path': unsolved_captcha_path})

            # Solve the captcha
            solved_captcha_path = os.path.join(
                CAPTCHA_STORAGE_PATH,
                captcha_time.strftime('%Y%m%d-%H%M%S') + '-solved.png'
            )
            pixels_to_move = solve_geetest_captcha(unsolved_captcha_path, solved_captcha_path)

            # Find the button
            slider_button = await page.querySelector('div.geetest_slider_button')
            slider_box = await slider_button.boundingBox()

            # Move to the button
            time.sleep(2)
            await page.mouse.move(
                slider_box['x'] + slider_box['width'] / 2,
                slider_box['y'] + slider_box['height'] / 2
            )
            await page.mouse.down()
            time.sleep(random.randrange(1, 5))

            # Move the button
            for i in range(
                    int(slider_box['x'] + slider_box['width'] / 2),
                    int(slider_box['x'] + slider_box['width'] / 2 + pixels_to_move)
            ):
                await page.mouse.move(i, slider_box['y'] + slider_box['height'] / 2)
                time.sleep(0.01)
            time.sleep(random.randrange(1, 5))
            await page.mouse.up()
            time.sleep(0.3)

            # Take a snapshot of what happens
            just_solved_captcha_path = os.path.join(
                CAPTCHA_STORAGE_PATH,
                captcha_time.strftime('%Y%m%d-%H%M%S') + '-page_solved.png'
            )
            await bg.screenshot({'path': just_solved_captcha_path})

            # See what happens here
            try:
                await page.waitForSelector(loaded_selector, {'timeout': 60000})
                captcha_flag = False
                break
            except TimeoutError:
                print('the loaded selector timed out probably due to captcha failure')

            # Test for failure again i guess
            if await page.querySelector('div.geetest_slider_button') is not None:
                print('Captcha failed')
                captcha_flag = True
                time.sleep(15)
                await page.close()
                continue
            else:
                print('Maybe the website is super slow right now?')
                captcha_flag = True
                time.sleep(15)
                await page.close()
                continue

    if captcha_flag:

        # We failed
        print('all captcha solutions failed')
        return ''

    else:

        # To get here the page should've loaded successfully, grab the html!
        if loaded_selector == 'object[type][data]':
            pdf_object = await page.waitForSelector(loaded_selector)
            link_href = await page.evaluate('(element) => element.data', pdf_object)

            # Create unique path for download of pdf
            path = os.path.join(EQUIBASE_PDF_PATH,datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            try:
                os.mkdir(path)
            except OSError:
                print(f'Creation of the directory {path} failed')
                return

            # change default download behavior
            cdp = await page.target.createCDPSession()
            await cdp.send(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": path},
            )

            # click download link
            await page.click(f'a[href="{link_href.replace("https://www.equibase.com","").replace("/premium/","")}"')

            # wait until file downloads or timeout
            start_time = datetime.datetime.now()
            file_downloaded_flag = len(glob.glob(os.path.join(path, '*.pdf'))) == 1
            while not file_downloaded_flag and (datetime.datetime.now()-start_time)<datetime.timedelta(seconds=60):
                time.sleep(1)
                file_downloaded_flag = len(glob.glob(os.path.join(path, '*.pdf'))) == 1

            # Handle the case where we timed out
            if not file_downloaded_flag:
                os.rmdir(path)
                html = None
            else:
                html = glob.glob(os.path.join(path, '*.pdf'))[0]
        else:
            html = await page.evaluate('document.body.innerHTML', force_expr=True)

        # Close the page
        await page.close()

        # Return the html
        return html


def initialize_stealth_browser():
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_initialize_stealth_browser())


def shutdown_stealth_browser(browser):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_shutdown_stealth_browser(browser))


def get_html_from_page_with_captcha(browser, url, loaded_selector):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_html_scrape_with_captcha(browser, url, loaded_selector))


if __name__ == '__main__':
    browser = initialize_stealth_browser()
    reconnect_tor()
    tb_html = get_html_from_page_with_captcha(browser, 'https://www.equibase.com/static/entry/TAM052020USA-EQB.html', 'div.race-nav.center')
    print(tb_html)
    wr_html = get_html_from_page_with_captcha(browser, 'https://www.equibase.com/static/entry/WRD052020USA-EQB.html', 'div.race-nav.center')
    print(wr_html)
    shutdown_stealth_browser(browser)
