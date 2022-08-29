import os
import re
import sys
import json
import time
import random
import requests
from urllib.parse import unquote
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from upgrade_json import start_upgrade
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_URL = "https://www.google.com"
BASE_DIR = os.getcwd()

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504, 104],
    allowed_methods=frozenset(["HEAD", "POST", "PUT", "GET", "OPTIONS"])
)
adapter = HTTPAdapter(max_retries=retry_strategy)


def link_checker(link):
    try:
        return requests.get(link, timeout=5)
    except:
        return None


def check_existence(filename, code):
    result = False
    extensions = ["jpg", "jpeg", "png"]
    for extension in extensions:
        if os.path.exists(os.path.join(BASE_DIR, f'src/img/{filename}/{code}.{extension}')):
            result = True
    return result


def get_user_agent():
    agents = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (Linux; Android 5.0; SM-G920A) AppleWebKit (KHTML, like Gecko) Chrome Mobile Safari (compatible; "
        "AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html)",
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html) Chrome/W.X.Y.Z Safari/537.36",
        "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36 ("
        "compatible; Google-Read-Aloud; +https://developers.google.com/search/docs/advanced/crawling/overview-google"
        "-crawlers)",
        "Mozilla/5.0 (Linux; Android 7.0; SM-G930V Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/59.0.3071.125 Mobile Safari/537.36 (compatible; Google-Read-Aloud; "
        "+https://developers.google.com/search/docs/advanced/crawling/overview-google-crawlers)",
        "Mozilla/5.0 (Linux; Android 11; Pixel 2; DuplexWeb-Google/1.0) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/86.0.4240.193 Mobile Safari/537.36",
    ]
    return random.choice(agents)


class Browser(object):

    def __init__(self):
        self.response = None
        self.headers = self.get_headers()
        self.session = requests.Session()

    def get_headers(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/87.0.4280.88 Safari/537.36"
        }
        return self.headers

    def send_request(self, method, url, **kwargs):
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.response = self.session.request(method, url, **kwargs)


class GoogleSearchImagesAPI(Browser):

    def __init__(self):
        super().__init__()
        self.img_path = None
        self.search = None
        self.attempts = None
        self.attempt = 1

    def find_img(self, parameter):
        print(parameter)
        self.search = parameter
        data = {
            "q": self.search,
            "newwindow": 1,
            "source": "lnms",
            "tbm": "isch",
            "sa": "X",
            "biw": 1366,
            "bih": 636,
            "dpr": 1
        }

        self.send_request('GET', BASE_URL + f'/search',
                          params=data,
                          headers=self.headers)

        return self.find_occurrences()

    def get_soup(self):
        return BeautifulSoup(self.response.text, 'html.parser')

    def find_occurrences(self):
        link = None
        if self.response.status_code == 429:
            self.headers["User-Agent"] = get_user_agent()
        script_img_tags = self.get_soup().find_all('script')
        result_list = re.findall('(https?:\/\/[^ ]*\.(?:svg|png|jpg|jpeg))', str(script_img_tags))
        if len(result_list) == 0:
            result_list = re.findall(r'(?:https://encrypted-tbn0[^ ]*(?:",))', str(script_img_tags))
            for result in result_list:
                link = result.split(',["')[-1].replace('"', '').split(',')[0].encode("latin1").decode('unicode-escape')
                if link.startswith("https://encrypted-tbn0.gstatic.com"):
                    link = unquote(link)
            return link
        else:
            for result in result_list:
                if len(result.split(',["')) > 1 and 'static01' not in result:
                    link = result.split(',["')[-1].replace('"', '')
                    if "," in link:
                        link = link.split(",")[0]
                    if link_checker(link):
                        return unquote(link).encode("latin1").decode('unicode-escape')
        self.attempt += 1
        if self.attempt > self.attempts:
            return ""
        time.sleep(5)
        self.find_img(self.search)

    def download_img(self, url_img, name_img, base_dir):
        if ".jpg" not in url_img and ".png" not in url_img and ".jpeg" not in url_img and "fbsbx.com":
            self.send_request("GET", url_img, headers=self.headers)
            content_tag_url = re.findall(r'<link rel="alternate" media=".*?" href="(.*?)" />', self.response.text)[0]
            self.send_request("GET", content_tag_url, headers=self.headers)
            content_img_url = re.findall(r'<meta name="twitter:image" content="(.*?)" />', self.response.text)[0]
            url_img = content_img_url.replace("amp;", "")
        file_path = os.path.join(BASE_DIR, f'src/img/{base_dir}')
        if not os.path.exists(file_path):
            os.makedirs(file_path, exist_ok=True)
        basename = os.path.basename(url_img).split('.')[-1] if '?v=' not in url_img \
            else os.path.basename(url_img).split('?v=')[0].split('.')[-1]

        if "jpg" != basename and "png" != basename and "jpeg" != basename:
            basename = "jpg"
        self.img_path = f"{file_path}/{name_img}.{basename}"

        self.send_request("GET", url_img, headers=self.headers, stream=True)
        if self.response.headers.get('content-type') == "image/webp":
            buffer = BytesIO(self.response.content)
            image = Image.open(buffer).convert('RGB')
            image.save(self.img_path)
        else:
            with open(self.img_path, 'wb') as file:
                for chunk in self.response.iter_content(chunk_size=1024):
                    file.write(chunk)
            return self.img_path

    def search_image_by_name(self, object_data, base_dir, extra_name=None):
        if not check_existence(base_dir, object_data["code"]):
            phrase = object_data.get("description") or object_data.get("name")
            print(
                f'\n{index} --> BUSCAR POR: {phrase} CÓDIGO: {object_data["code"]}')
            self.attempts = 3
            url = self.find_img(f'{extra_name + " " + phrase if extra_name else phrase}')
            if url:
                print("URL: ", url)
                self.download_img(url, object_data["code"], base_dir)
            else:
                print("URL NÃO ENCONTRADA!")
            time.sleep(1)
        else:
            print(f'\r{item["code"]} JÁ ESTÁ SALVO.', end="")


if __name__ == '__main__':
    args = sys.argv
    gsia = GoogleSearchImagesAPI()
    filename = args[1 if len(args) > 1 else exit()]
    with open(filename, "r") as json_data:
        data = json.load(json_data)
    index = 0
    basename = os.path.basename(filename).split('.')[0]
    for item in data.get(basename):
        index += 1
        gsia.search_image_by_name(item, "grupos")
        for sub_item in item["products"]:
            index += 1
            gsia.search_image_by_name(sub_item, "produtos", item.get("name"))
    print(f'\rITEMS JÁ ESTÃO SALVOS.', end="")
    start_upgrade(filename, None)
