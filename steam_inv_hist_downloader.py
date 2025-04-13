import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv

EXPORT_CSV_PATH = './steam_inv_trans_list.csv'
DEBUG = False
###################################################
#   Access control variables/config
###################################################

STEAM_ACCOUNT_ID = input('Provide your account ID (log into steam in your browser and go to your profile, the ID is the number that appears at the end of the url. Like this example: https://steamcommunity.com/profiles/99999999999999999/):\n')
SESSION_ID = input('Provide your session ID (log into steam in your browser and get this data from a cookie named "sessionid"):\n')
SECURE_LOGIN_TOKEN = input('Provide your secure login token (log into steam in your browser and get this data from a cookie named "steamLoginSecure"):\n')


###################################################
#   Steam endpoint and headers/cookies config
###################################################

steam_inventory_endpoint = f"https://steamcommunity.com:443/profiles/{STEAM_ACCOUNT_ID}/inventoryhistory/"
params = {
    'l': 'english',
    'ajax': 1
}

request_cookies = {
    "sessionid": SESSION_ID,
    "steamLoginSecure": SECURE_LOGIN_TOKEN,
    "timezoneOffset2": "7200,0"
}

request_headers = {
    "Sec-Ch-Ua": "\"Chromium\";v=\"135\", \"Not-A.Brand\";v=\"8\"",
    "Sec-Ch-Ua-Mobile": "?0", "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Referer": f"https://steamcommunity.com/profiles/{STEAM_ACCOUNT_ID}/inventory/",
    "Accept-Encoding": "gzip, deflate, br",
    "Priority": "u=0, i",
    "Connection": "keep-alive"
}

#   Given a specific instance of the html, returns the list of all transactions in it
def scrap_item_list_from_html(html, since):
    inv_trans_list = []
    soup = BeautifulSoup(html, 'html.parser')
    # Search for all transactions
    rows = soup.select('.tradehistoryrow')
    for row in rows:
        date = row.select_one('.tradehistory_date').contents[0].strip()
        time = row.select_one('.tradehistory_timestamp').text.strip()
        parsed_date = datetime.strptime(f'{date} {time}', "%d %b, %Y %I:%M%p")
        parsed_date_ts = parsed_date.timestamp()
        if parsed_date_ts < since:
            DEBUG and print(f'Skipping current transaction because is too old (older than the requested time range).\nTransaction date is: {parsed_date}')
            continue
        description = row.select_one('.tradehistory_event_description').text.strip()
        #   Steam shows incoming items as a "+" here and outgoing items as a "-"
        sign = row.select_one('.tradehistory_items_plusminus')
        sign = sign.text.strip() if sign else '?'
        #   Get the names (multiples names might appear in a single transaction. For example, when trading multiple items at once)
        items = row.select('.history_item_name')
        item_names = [item.text.strip() for item in items]
        #print(f"{date} {time} | {sign} | {description}")
        #   Append to the list of transactions
        for name in item_names:
            inv_trans_list.append([parsed_date, sign, description, name])
            DEBUG and print(f'Added transaction: {[parsed_date, sign, description, name]}')
            #print(f"   - {name}")
    return inv_trans_list

#   Handles requests to Steam's endpoint as well as pagination
def download_steam_inv_since(since):
    inv_trans_list = []
    cursor = 'first_iter_placeholder'   #   For 1st iteration it won't be used, for subsequent ones it will be properly populated
    while cursor:
        #   Do request send step by step to be able to print extra debug info
        session = requests.Session()
        req = requests.Request('GET', steam_inventory_endpoint, params=params, headers=request_headers, cookies=request_cookies)
        prepped = session.prepare_request(req)
        if DEBUG:
            print("Request URL:", prepped.url)
            print("Request Headers:", prepped.headers)
            print("Request Method:", prepped.method)
            print("Request Body:", prepped.body)
        response = session.send(prepped)
        if response.status_code != 200:
            print(f'Error accessing Steam inv. Error received is: {response.status_code}')
            return inv_trans_list

        #   Parse the AJAX data, contains the HTML data required for the browser to show newly arrived items and also the cursor, which points into the next page
        data = response.json()
        html = data['html']
        cursor = data['cursor'] if 'cursor' in data else None

        #   Process new data and add to the list
        inv_trans_list_size = len(inv_trans_list)
        inv_trans_list += scrap_item_list_from_html(html=html, since=since)
        DEBUG and print(f'Response processed, {len(inv_trans_list) - inv_trans_list_size} items were added to the list.')
        #   Cursor will be None in last request (allegedly)
        if cursor:
            #   Generate cursor parameters in the weird way steam does. Final url should look something like:
            #ajax=1&cursor[time]=1344396790&cursor[time_frac]=0&cursor[s]=7777777777
            for key in cursor:
                params[f'cursor[{key}]'] = cursor[key]

            DEBUG and print(f'Received cursor: {cursor}')
            DEBUG and print(f'New params are: {params}')
            #   If cursor already older than since, quit (otherwise, this request would only retrieve transactions older than cursor, which would be older than the "since")
            if 'time' in cursor:
                try:
                    cursor_int = int(cursor['time'])
                    if cursor_int < since:
                        DEBUG and print(f'Old cursor detected: {cursor}. Pagination is finished, no more requests will be sent.')
                        break
                except:
                    print(f'Couldn\'t parse int from cursor. Cursor value: "{cursor}"')
        #   3s should be enough, https://github.com/Citrinate/BoosterManager/blob/master/BoosterManager/Docs/InventoryHistory.md points at a rate limit of 25req/min
        #   but I'd rather stay on the safe side, since speed is not a requirement here
        time.sleep(5)
    return inv_trans_list

if __name__ == '__main__':
    date_str_to_download_from = input('Input the date you want to download transactions from (with the format 01/04/2000 00:00:00):\n')
    #   If provided date gives us ANY trouble, just download everything
    try:
        dt_to_download_from = datetime.strptime(date_str_to_download_from, "%d/%m/%Y %H:%M:%S")
    except:
        date_str_to_download_from = '11/06/2000 00:00:00'
        dt_to_download_from = datetime.strptime(date_str_to_download_from, "%d/%m/%Y %H:%M:%S")

    ts_to_download_from = int(dt_to_download_from.timestamp())
    print(f'Downloading data since {date_str_to_download_from} ({ts_to_download_from})')

    #   Download transactions since specified date
    transaction_list = download_steam_inv_since(ts_to_download_from)

    #   Export to csv
    with open(EXPORT_CSV_PATH, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(transaction_list)

