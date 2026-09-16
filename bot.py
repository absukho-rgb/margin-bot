import re
import time
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# 1. 텔레그램 정보만 입력 (네이버 API 키 불필요!)
# ==============================================================================
TELEGRAM_TOKEN = "8209783129:AAEXIBT9MMqOf4xPVonqRULyeNTVZrVBFzA"
TELEGRAM_CHAT_ID = "5883504932"

# 🎯 마진 및 비용 조건
MIN_MARGIN = 3000          # 최소 순마진 3,000원 이상
FIXED_SHIPPING_FEE = 3000   # 배송비 3,000원 (고정)
PLATFORM_FEE_RATE = 0.10   # 수수료 10%

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==============================================================================
# 2. 텔레그램 알림 전송
# ==============================================================================
def send_telegram(text):
    if "YOUR_TELEGRAM" in TELEGRAM_TOKEN:
        print("[텔레그램 키 미입력]\n" + text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"텔레그램 발송 에러: {e}")

# ==============================================================================
# 3. 수량 파싱 및 키워드 정제
# ==============================================================================
def parse_bundle_quantity(title):
    plus_match = re.search(r'(\d+)\+(\d+)', title)
    if plus_match:
        return int(plus_match.group(1)) + int(plus_match.group(2))
    count_match = re.search(r'(\d+)\s*(개|팩|종|세트|병|포|box|박스)', title, re.IGNORECASE)
    if count_match:
        return int(count_match.group(1))
    return 1

def clean_title(title):
    cleaned = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    cleaned = re.sub(r'(\d+)\+(\d+)|(\d+)\s*(개|팩|종|세트|병|포)', '', cleaned)
    words = [w for w in cleaned.split() if len(w) > 1]
    return " ".join(words[:4]) if words else title[:15]

# ==============================================================================
# 4. 네이버 쇼핑 웹 크롤링 (API 키 없이 최저가 추출)
# ==============================================================================
def get_naver_price_crawling(keyword):
    search_url = f"https://search.shopping.naver.com/search/all?query={requests.utils.quote(keyword)}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            # 네이버 쇼핑 페이지에서 가격 숫자(lprice) 수집
            prices = re.findall(r'"lprice":"(\d+)"', res.text)
            if prices:
                lowest_price = int(prices[0])
                return lowest_price, search_url
    except Exception as e:
        print(f"네이버 크롤링 에러: {e}")
    return None, None

# ==============================================================================
# 5. 홈쇼핑모아 수집 및 마진 3,000원 검증
# ==============================================================================
def check_hsmoa():
    try:
        res = requests.get("https://hsmoa.com/", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select(".timeline-item, .deal-item, .product-item")

        for item in items:
            t = item.select_one(".title, .name, .product-name")
            p = item.select_one(".price, .product-price")
            if not t or not p:
                continue

            raw_title = t.text.strip()
            buy_price = int(re.sub(r"[^\d]", "", p.text))
            qty = parse_bundle_quantity(raw_title)
            unit_buy_price = buy_price / qty
            base_keyword = clean_title(raw_title)

            # API 없이 네이버 최저가 웹 크롤링
            price_naver, link_naver = get_naver_price_crawling(base_keyword)

            if price_naver:
                # 마진 공식: 네이버가 - 수수료(10%) - 개당사입가 - 배송비(3,000원)
                margin = price_naver - (price_naver * PLATFORM_FEE_RATE) - unit_buy_price - FIXED_SHIPPING_FEE

                if margin >= MIN_MARGIN:
                    coupang_url = f"https://www.coupang.com/np/search?q={requests.utils.quote(base_keyword)}"
                    msg = (
                        f"🔥 <b>[홈쇼핑모아 고마진 상품 발견!]</b>\n\n"
                        f"📦 <b>상품명:</b> {raw_title}\n"
                        f"💵 <b>사입가:</b> {buy_price:,}원 (개당 {int(unit_buy_price):,}원)\n"
                        f"🏷 <b>네이버 최저가:</b> {price_naver:,}원\n"
                        f"🚚 <b>배송비:</b> 3,000원 (고정)\n"
                        f"💰 <b>예상 순마진: {int(margin):,}원</b>\n\n"
                        f"🔗 <a href='{link_naver}'>네이버 최저가 확인</a>\n"
                        f"🚀 <a href='{coupang_url}'>쿠팡 최저가 검색</a>"
                    )
                    send_telegram(msg)

            time.sleep(1)

    except Exception as e:
        print(f"크롤링 에러: {e}")

if __name__ == "__main__":
    check_hsmoa()
