import random
import time
import json
import os
import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import List, Dict, Optional
import socket
from urllib3.exceptions import ConnectTimeoutError
from decouple import config
from steam.webapi import WebAPI


#######################################
#           全局配置项（统一管理）         #
#######################################

class SteamConfig:
    # 请求配置
    REQUEST_HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Origin": "https://store.steampowered.com",
        "Referer": "https://store.steampowered.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }

    # 超时与重试配置
    CONNECT_TIMEOUT = 20
    READ_TIMEOUT = 30
    MAX_RETRIES = 5
    RETRY_DELAY = lambda attempt: min(2 ** attempt, 60)

    # 速率限制配置
    RATE_LIMIT = 10
    REQUEST_DELAY = (3, 7)

    # Cookie和会话配置
    COOKIES = {
        "sessionid": "c6f0fe4d6bae758d1b10d3c3",
        "steamLoginSecure": "76561199160723252%7C%7CeyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAxN18yNURFQkEyNl9BOEM0RiIsICJzdWIiOiAiNzY1NjExOTkxNjA3MjMyNTIiLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3NDQ2ODE1MTcsICJuYmYiOiAxNzM1OTU0OTkzLCAiaWF0IjogMTc0NDU5NDk5MywgImp0aSI6ICIwMDE5XzI2MjA2RkY1XzIwNDJEIiwgIm9hdCI6IDE3NDA0ODUzNDEsICJydF9leHAiOiAxNzU4NDUwODQ1LCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiNDUuMTk1LjIzLjE4IiwgImlwX2NvbmZpcm1lciI6ICI0NS4xOTUuMjMuMTgiIH0.NC-NQMR5LnB08hmUB7uAOv7Kph-QYXP00ACskKAGlu4VClV4qM50xVN-H-FZ9T3zA7zdtGiykgK9B_XNy5wuAQ",
    }

    # API端点
    API_URL = "https://store.steampowered.com/api/appdetails"
    STORE_URL = "https://store.steampowered.com"

    # 分批保存配置
    BATCH_SIZE = 50
    OUTPUT_FILE = "../steam_games_data.csv"
    APP_LIST_FILE = "../steam_app_list.json"


#######################################
#           核心功能实现               #
#######################################

class SteamCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SteamConfig.REQUEST_HEADERS)
        self.session.cookies.update(SteamConfig.COOKIES)
        self.rate_limiter = threading.Semaphore(SteamConfig.RATE_LIMIT)
        self.results = []
        self.batch_counter = 0

    def clean_html_to_dict(self, html_text: str) -> Dict[str, str]:
        """解析HTML格式的系统需求"""
        if not html_text or html_text == 'N/A':
            return {}
        soup = BeautifulSoup(html_text, 'html.parser')
        requirements = {}
        for li in soup.find_all('li'):
            li_text = li.get_text(separator=' ', strip=True)
            if match := re.search(r'(.+?):\s*(.+)', li_text):
                requirements[match.group(1).strip()] = match.group(2).strip()
        return requirements

    def load_app_list_from_file(self) -> List[int]:
        """从JSON文件中加载appid列表"""
        if not os.path.exists(SteamConfig.APP_LIST_FILE):
            raise FileNotFoundError(f"文件 {SteamConfig.APP_LIST_FILE} 不存在")

        with open(SteamConfig.APP_LIST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [app['appid'] for app in data['applist']['apps']]

    def get_random_appids(self, count: int = 300) -> List[int]:
        """获取随机appid"""
        try:
            app_list = self.load_app_list_from_file()
            if len(app_list) >= count:
                return random.sample(app_list, count)
            print(f"警告：Steam只有{len(app_list)}个应用，返回全部")
            return app_list
        except Exception as e:
            print(f"获取appid失败: {e}")
            return []

    def save_to_csv(self, batch_data: List[Dict], mode: str = 'a'):
        """保存数据到CSV（追加或覆盖模式）"""
        if not batch_data:
            return

        df = pd.DataFrame(batch_data)
        file_exists = os.path.exists(SteamConfig.OUTPUT_FILE)

        # 只在文件不存在或为覆盖模式时写入header
        header = not file_exists or mode == 'w'

        try:
            # 使用文件锁确保线程安全
            with threading.Lock():
                df.to_csv(
                    SteamConfig.OUTPUT_FILE,
                    mode=mode,
                    header=header,
                    index=False,
                    encoding='utf-8-sig'  # 确保中文等特殊字符正确保存
                )
            tqdm.write(f"成功保存批次 {self.batch_counter} (共 {len(batch_data)} 条记录) 到 {SteamConfig.OUTPUT_FILE}")
            return True
        except Exception as e:
            tqdm.write(f"保存批次 {self.batch_counter} 失败: {e}")
            return False

    def get_app_details(self, app_id: int, cc: str = 'us', l: str = 'en') -> Optional[Dict]:
        """获取单个应用详情（带重试和超时处理）"""
        params = {"appids": app_id, "cc": cc, "l": l}
        for attempt in range(SteamConfig.MAX_RETRIES):
            try:
                with self.rate_limiter:
                    time.sleep(random.uniform(*SteamConfig.REQUEST_DELAY))
                    response = self.session.get(
                        SteamConfig.API_URL,
                        params=params,
                        timeout=(SteamConfig.CONNECT_TIMEOUT, SteamConfig.READ_TIMEOUT)
                    )
                    if response.status_code == 429:
                        delay = SteamConfig.RETRY_DELAY(attempt)
                        tqdm.write(f"Rate limited. Waiting {delay}s (appid: {app_id})")
                        time.sleep(delay)
                        continue
                    response.raise_for_status()
                    data = response.json()

                    # 使用新的游戏判断逻辑
                    if not data.get(str(app_id), {}).get('success', False):
                        return None

                    game_data = data[str(app_id)]['data']
                    if game_data.get('type', '').lower() != 'game':
                        return None

                    # 处理可能为列表或字符串的pc_requirements
                    pc_req = game_data.get('pc_requirements', {})
                    min_req = pc_req.get('minimum', 'N/A') if isinstance(pc_req, dict) else pc_req
                    rec_req = pc_req.get('recommended', 'N/A') if isinstance(pc_req, dict) else pc_req

                    # 使用新的数据解析方式
                    return {
                        'appid': app_id,
                        'name': game_data.get('name', 'N/A'),
                        'price': game_data.get('price_overview', {}).get('final_formatted', 'Free'),
                        'recommendations': game_data.get('recommendations', {}).get('total', 'N/A'),
                        'metacritic': game_data.get('metacritic', {}).get('score', 'N/A'),
                        'controller_support': game_data.get('controller_support', 'N/A'),
                        'developers': ", ".join(game_data.get('developers', ['N/A'])),
                        'publishers': ", ".join(game_data.get('publishers', ['N/A'])),
                        'platforms_windows': game_data.get('platforms', {}).get('windows', False),
                        'platforms_mac': game_data.get('platforms', {}).get('mac', False),
                        'platforms_linux': game_data.get('platforms', {}).get('linux', False),
                        'release_date': game_data.get('release_date', {}).get('date', 'N/A'),
                        'minimum_req': self.clean_html_to_dict(min_req),
                        'recommended_req': self.clean_html_to_dict(rec_req),
                        'categories': [cat['description'] for cat in game_data.get('categories', [])],
                        'genres': [genre['description'] for genre in game_data.get('genres', [])],
                        'header_image': game_data.get('header_image', 'N/A'),
                    }
            except (requests.exceptions.RequestException, socket.timeout) as e:
                delay = SteamConfig.RETRY_DELAY(attempt)
                tqdm.write(f"Error (attempt {attempt + 1}): {e}. Waiting {delay}s")
                time.sleep(delay)
        return None

    def crawl_apps(self, app_ids: List[int], max_workers: int = 5):
        """爬取多个应用，分批保存"""
        self.results = []
        self.batch_counter = 0
        file_exists = os.path.exists(SteamConfig.OUTPUT_FILE)

        # 如果文件已存在，先读取已有数据以避免重复
        existing_appids = set()
        if file_exists:
            try:
                existing_df = pd.read_csv(SteamConfig.OUTPUT_FILE)
                existing_appids = set(existing_df['appid'].astype(str))
            except:
                pass

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.get_app_details, app_id): app_id
                       for app_id in app_ids if str(app_id) not in existing_appids}

            for future in tqdm(as_completed(futures), total=len(futures), desc="Crawling Apps"):
                if result := future.result():
                    self.results.append(result)
                    if len(self.results) >= SteamConfig.BATCH_SIZE:
                        if self.save_to_csv(self.results):
                            self.results = []  # 只在保存成功后清空
                            self.batch_counter += 1
                else:
                    tqdm.write(f"\nApp {futures[future]} 不是游戏或获取失败，跳过...")

        # 保存剩余未满批次的数据
        if self.results:
            self.save_to_csv(self.results)

    def get_hot_games(self, min_recommendations: int = 0) -> List[int]:
        """返回有推荐数据的游戏appid列表"""
        if not os.path.exists(SteamConfig.OUTPUT_FILE):
            return []

        try:
            df = pd.read_csv(SteamConfig.OUTPUT_FILE)
            df['recommendations'] = pd.to_numeric(df['recommendations'], errors='coerce')
            valid_games = df[df['recommendations'].notna() &
                             (df['recommendations'] >= min_recommendations)]
            appids = valid_games['appid'].tolist()
            print(f"找到 {len(appids)} 个游戏 (推荐数≥{min_recommendations})")
            return appids
        except Exception as e:
            print(f"获取热评游戏失败: {e}")
            return []


#######################################
#           主程序入口                 #
#######################################

def main():
    crawler = SteamCrawler()

    # 获取随机appid（示例使用50个）
    app_ids = crawler.get_random_appids(10000)

    # 爬取游戏数据
    crawler.crawl_apps(app_ids)

    # 获取热评游戏
    hot_games = crawler.get_hot_games()
    print(hot_games)


if __name__ == "__main__":
    main()