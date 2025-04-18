import os
import random
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import pandas as pd
import requests
from tqdm import tqdm


#######################################
#           全局配置项（统一管理）         #
#######################################

class SteamReviewConfig:
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
    REVIEW_API_URL = "https://store.steampowered.com/appreviews/{appid}?json=1&language=schinese&filter=recent&purchase_type=all&num_per_page=100"

    # 分批保存配置
    BATCH_SIZE = 50
    OUTPUT_FILE = "../dataset/steam_reviews_data.csv"

    # 要爬取评论的appid列表
    # TARGET_APPIDS = [
    #     367520,  # Hades
    #     292030,  # The Witcher 3
    #     730,  # CS:GO
    #     578080,  # PUBG
    #     570,  # Dota 2
    #     271590,  # GTA V
    #     1172470,  # Apex Legends
    #     1091500,  # Cyberpunk 2077
    #     1245620,  # ELDEN RING
    #     892970  # Valheim
    # ]
    TARGET_APPIDS = [1182830, 580170, 297760, 314790, 511740, 240440, 597180, 3990, 11180, 1425000, 686440, 1561040,
                     398710, 2193540, 356390, 1857090, 753660, 463930, 32620, 434420, 2273880, 331450, 1285000, 475490,
                     1612620, 406850, 3298820, 464920, 730830, 311290, 480650, 347620, 308060, 2696070, 431770, 1271710,
                     695600, 55000, 3068580, 302510, 2943930, 3253630, 324710, 798840, 2217000, 348360, 582270, 422110,
                     2352640, 599560, 733300, 1188080, 1372320, 336610, 1058130, 369530, 411570, 1716740, 1311070,
                     2179290, 351700, 1151130, 1530750, 2236860, 345640, 3377320, 304410, 2216360, 1408260, 2191050,
                     1127840, 589530, 665360, 590380, 3380360, 2277300, 1682340, 490450, 503370, 21030, 435150, 216890,
                     314240, 2642570, 979400, 423810, 1394800, 1109690, 1512710, 331160, 1096410, 237550, 1325310,
                     238240, 8190, 3362480, 10180, 225300, 389220, 2415240, 2103140, 2627570, 744050, 1442430, 235800,
                     1025600, 33570, 12360, 2282480, 1198090, 355520, 303940, 1463120, 601540, 349250, 2543650, 1258460,
                     1198740, 1930, 1431230, 1015890, 259660, 383270, 21090, 336610, 1420290, 2529770, 2176850, 2093910,
                     476700, 108110, 337360, 386360, 1428420, 404530, 356180, 237950, 1134100, 1274600, 1609160,
                     1607670, 1101270, 324650, 218760, 1057540, 411320, 498500, 2013580, 247660, 2162070, 476480,
                     1037020, 394760, 4500, 2776570, 2261050, 1262460, 22130, 415350, 2243110, 31220, 349730, 2203040,
                     489360, 1378040, 553850, 926540, 71340, 1462810, 2286790, 1092790, 1416920, 1730250, 224500,
                     443000, 2146170, 23400, 3107930, 332390, 42230, 3259040, 1437880, 1020820, 22450, 965230, 979600,
                     2782610, 206250, 1812620, 1320100, 386080, 1392060, 1341900, 1418360, 383840, 7620, 350070, 233310,
                     391170, 763250, 16730, 1430970, 1599250, 379720, 365580, 342640, 2435180, 524390, 742520, 1257430,
                     1422440, 1006270, 1338580, 2817140, 978460, 774861, 1200730, 233680, 204100, 361890, 334230,
                     219760, 15560, 1345890, 526870, 581320, 351910, 2336590, 2187220, 339830, 17340, 2776500, 314070,
                     466800, 1606280, 1097580, 2649480, 411830, 1399670, 444480, 440640, 20920, 1065180, 781810,
                     2558200, 1566540, 348290, 976390, 1283190, 1043810, 713530, 1437500, 375460, 388880, 2184770,
                     1602490, 481510, 1191900, 7760, 595460, 801550, 34900, 1200110, 216910, 2263920, 253900, 1671280,
                     3172280, 2312770, 1519790, 2331330, 2014910, 397950, 1369760, 1346960, 38460, 1390350, 432940,
                     348950, 2281480, 1601970, 885000, 1125910, 3229170, 1361510, 1434480, 1517970, 1708850, 1123050,
                     1679290, 333430, 1049410, 2812480, 221540, 597840, 394510, 601150, 1121590, 259390, 390220,
                     2520980, 1528050, 1594130, 2942700, 349730, 259980, 3075800, 1106830, 330350, 2088650, 207750,
                     34600, 895870, 369890, 315210, 401360, 298240, 2628570, 329070, 591420, 2544720, 1323420, 2164310,
                     596240, 759570, 2294450, 1975340, 1174180, 1343670, 366870, 1051410, 2313240, 1648190, 2167220,
                     388980, 495700, 1205960, 373930, 2089450, 390340, 1436590, 413710, 2187290, 950740, 2998970,
                     378690, 282560, 233130, 1370170, 2517200, 774281, 264220, 1126990, 228960, 335620, 38700, 237970,
                     926990, 1915380, 1121640, 434210, 422910, 411330, 2259310, 40700, 2443630, 2315690, 1457220,
                     1542790, 1331510, 2943280, 211120, 395170, 1677970, 1325890, 2055290, 1366810, 2751000, 1889620,
                     4720, 2644610, 4570, 35320, 1111450, 1656640, 340730, 497850, 1398740, 1034140, 2060870, 301740,
                     2158740, 2352040, 462930, 230980, 242680, 406130, 2354000, 454530, 454160, 1442170, 519080, 461700,
                     295630, 505230, 2683150, 234650, 1610440, 514920, 315850, 1677980, 365660, 351700, 1186040, 987230,
                     448910, 1185490, 455910, 2515020, 808010, 595500, 890520, 242700, 411000, 34410, 2280060, 402160,
                     2221920, 2196980, 240340, 448510, 1489410, 415830, 654890, 58200, 22360, 2223740, 2254710, 2618840,
                     963690, 250520, 716380, 465760, 332500, 415480, 31100, 1694430, 370280, 400580, 1242670, 357900,
                     1324340, 1689350, 733050, 397310, 2595860, 2180550, 2915950, 586310, 296470, 331750, 441280, 39660,
                     521430, 2581570, 2777230, 1410710, 1236720, 323850, 1425250, 1140890, 2442380, 2581750, 356650,
                     2839450, 1695840, 760810, 1542280, 435790, 2311190, 1357210, 1424860, 391580, 377530, 33900,
                     1132970, 1371690, 334310, 2767520, 1180660, 1700, 2929730, 1361230, 2264020, 2438990, 835570,
                     37210, 428200, 351290, 3380, 1265090, 2864210, 406870, 2022090, 341020, 3081810, 1999520, 47810,
                     2158670, 351870, 38600, 497180, 3161850, 1594130, 261510, 400110, 352240, 596620, 2249850, 332580,
                     381750, 1973080, 2281940, 427730, 453100, 718650, 2817690, 1386650, 2406770, 1186400, 2443090,
                     936790, 445980, 1189780, 3265280, 421810, 2094270, 1679510, 1203220, 312840, 1458920, 2095090,
                     1303740, 512020, 240600, 427190, 2800520, 1140270, 1262600, 1205170, 63209, 1036120, 2140330,
                     968550, 1419160, 317100, 3084280, 2413620, 346040, 448000, 12180, 1544540, 1131400, 595430, 232910,
                     1471200, 1334000, 1590760, 6870, 502230, 511090, 3175860, 202860, 65530, 1018160, 3505840, 2348730,
                     2291760, 1035660, 253410, 7510, 1605220, 374410, 695970, 1903910, 878750, 1197220, 434190, 965320,
                     1965190, 345540, 12460, 214570, 420980, 587470, 301200, 499620, 404200, 39650, 1647730, 1316560,
                     602520, 1634860, 2285570, 1388770, 1191210, 2644470, 1458690, 1689080, 1972440, 463290, 620980,
                     211500, 1424720, 1755910, 311770, 1450100, 2236240, 1545990, 2081470, 321960, 444690, 402180,
                     774181, 414340, 2477010, 420930, 394680, 404690, 1159520, 1044980, 370480, 984470, 2060590,
                     2983270, 339440, 1985810, 1457740, 10680, 1668780, 376300, 2219450, 40930, 1336060, 3241660,
                     1406990, 773670, 2231040, 3241490, 1197770, 252330, 2320910, 306200, 2593900, 1605010, 207080,
                     15400, 2247570, 259190, 1663220, 38400, 1487390, 2419900, 1010270, 770070, 248530, 1660990, 960190,
                     2330750, 348460, 986020, 15560, 304240, 400750, 2060480, 1418020, 330720, 1182900, 1399370,
                     1252710, 2479290, 410850, 1640, 37420, 2113850, 12140, 1256230, 460340, 1309620, 212630, 449210,
                     2348610, 1565080, 1909770, 1430640, 2160360, 1461740, 461170, 1316700, 32770, 352220, 464340,
                     1021690, 2131200, 514090, 1042920, 1841640, 1700, 514310, 402880, 1107370, 429050, 2292060, 698670,
                     965820, 1044490, 1983690, 2368300, 2278630, 2067790, 1403830, 1507720, 1045610, 1146310, 427550,
                     2694490, 1094390, 396160, 332250, 344820, 978300, 2246110, 1328670, 1203360, 450440, 2151290,
                     2821850, 1265850, 416550, 1198730, 1508360, 297310, 244430, 38480, 521350, 257120, 2257720, 837510,
                     477160, 714800, 463760, 421660, 1503670, 1205960, 893020, 11020, 1430420, 2005160, 1506440, 367270,
                     577730, 1149550, 2906370, 2076580, 726950, 1116880, 961490, 1432100, 2340650, 49900, 48700,
                     2584650, 1184790, 233210, 1264970, 1888930, 333250, 2539350, 234940, 1000030]

    # 无意义评论的正则表达式
    MEANINGLESS_PATTERNS = [
        r'^[\W_]+$',  # 纯符号
        r'^[^\w]{10,}$',  # 超过10个非字母数字字符
        r'^(.+?)\1{3,}$',  # 重复内容超过3次
        r'^[A-Za-z0-9]{1,3}$',  # 只有1-3个字符
        r'^[\s\W]+$',  # 只有空白和符号
        r'^.{1,5}$',  # 非常短的评论
    ]

    # 富文本标签正则表达式
    RICH_TEXT_PATTERN = r'\[/?[a-zA-Z0-9]+\]'


#######################################
#           核心功能实现               #
#######################################

class SteamReviewCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SteamReviewConfig.REQUEST_HEADERS)
        self.session.cookies.update(SteamReviewConfig.COOKIES)
        self.rate_limiter = threading.Semaphore(SteamReviewConfig.RATE_LIMIT)
        self.results = []
        self.batch_counter = 0

    def is_meaningless_review(self, text: str) -> bool:
        """检查评论是否无意义"""
        if not text or len(text.strip()) == 0:
            return True

        text = text.strip()
        for pattern in SteamReviewConfig.MEANINGLESS_PATTERNS:
            if re.fullmatch(pattern, text):
                return True
        return False

    def clean_review_text(self, text: str) -> str:
        """清理评论内容"""
        if not text:
            return ""

        # 移除富文本标签
        text = re.sub(SteamReviewConfig.RICH_TEXT_PATTERN, '', text)

        # 移除多余空白
        text = ' '.join(text.split())

        return text.strip()

    def save_to_csv(self, batch_data: List[Dict], mode: str = 'a'):
        """保存数据到CSV（追加或覆盖模式）"""
        if not batch_data:
            return

        columns_order = ['appid', 'review_id', 'author_id', 'is_recommended', 'playtime_forever', 'review_text']
        df = pd.DataFrame(batch_data)[columns_order]
        file_exists = os.path.exists(SteamReviewConfig.OUTPUT_FILE)

        # 只在文件不存在或为覆盖模式时写入header
        header = not file_exists or mode == 'w'

        try:
            # 使用文件锁确保线程安全
            with threading.Lock():
                df.to_csv(
                    SteamReviewConfig.OUTPUT_FILE,
                    mode=mode,
                    header=header,
                    index=False,
                    encoding='utf-8-sig'  # 确保中文等特殊字符正确保存
                )
            tqdm.write(
                f"成功保存批次 {self.batch_counter} (共 {len(batch_data)} 条记录) 到 {SteamReviewConfig.OUTPUT_FILE}")
            return True
        except Exception as e:
            tqdm.write(f"保存批次 {self.batch_counter} 失败: {e}")
            return False

    def get_game_reviews(self, app_id: int) -> Optional[List[Dict]]:
        """获取单个游戏的评论（带重试和超时处理）"""
        url = SteamReviewConfig.REVIEW_API_URL.format(appid=app_id)

        for attempt in range(SteamReviewConfig.MAX_RETRIES):
            try:
                with self.rate_limiter:
                    time.sleep(random.uniform(*SteamReviewConfig.REQUEST_DELAY))
                    response = self.session.get(
                        url,
                        timeout=(SteamReviewConfig.CONNECT_TIMEOUT, SteamReviewConfig.READ_TIMEOUT))

                    if response.status_code == 429:
                        delay = SteamReviewConfig.RETRY_DELAY(attempt)
                        tqdm.write(f"Rate limited. Waiting {delay}s (appid: {app_id})")
                        time.sleep(delay)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if not data.get('success', False):
                        return None

                    reviews = []
                    for review in data.get('reviews', []):
                        # 清理评论内容
                        review_text = self.clean_review_text(review.get('review', ''))

                        # 跳过无意义评论
                        if self.is_meaningless_review(review_text):
                            continue

                        reviews.append({
                            'appid': app_id,  # 新增appid字段
                            'review_id': review.get('recommendationid', ''),
                            'author_id': review.get('author', {}).get('steamid', ''),
                            'is_recommended': review.get('voted_up', False),
                            'playtime_forever': review.get('author', {}).get('playtime_forever', 0),
                            'review_text': review_text
                        })

                    return reviews

            except (requests.exceptions.RequestException, socket.timeout) as e:
                delay = SteamReviewConfig.RETRY_DELAY(attempt)
                tqdm.write(f"Error (attempt {attempt + 1}): {e}. Waiting {delay}s")
                time.sleep(delay)
        return None

    def crawl_reviews(self, max_workers: int = 5):
        """爬取多个游戏的评论，分批保存"""
        self.results = []
        self.batch_counter = 0
        file_exists = os.path.exists(SteamReviewConfig.OUTPUT_FILE)

        # 如果文件已存在，先读取已有数据以避免重复
        existing_review_ids = set()
        if file_exists:
            try:
                existing_df = pd.read_csv(SteamReviewConfig.OUTPUT_FILE)
                existing_review_ids = set(existing_df['review_id'].astype(str))
            except:
                pass

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.get_game_reviews, app_id): app_id
                       for app_id in SteamReviewConfig.TARGET_APPIDS}

            for future in tqdm(as_completed(futures), total=len(futures), desc="Crawling Reviews"):
                if result := future.result():
                    # 过滤掉已存在的评论
                    new_reviews = [r for r in result if str(r['review_id']) not in existing_review_ids]
                    self.results.extend(new_reviews)

                    if len(self.results) >= SteamReviewConfig.BATCH_SIZE:
                        if self.save_to_csv(self.results):
                            self.results = []  # 只在保存成功后清空
                            self.batch_counter += 1
                else:
                    tqdm.write(f"\nApp {futures[future]} 获取评论失败，跳过...")

        # 保存剩余未满批次的数据
        if self.results:
            self.save_to_csv(self.results)


#######################################
#           主程序入口                 #
#######################################

def main():
    crawler = SteamReviewCrawler()
    crawler.crawl_reviews()


if __name__ == "__main__":
    main()
