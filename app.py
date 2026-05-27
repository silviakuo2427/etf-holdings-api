from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import re

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

holdings_cache = {}
last_updated = None

ETF_META = {
    "00980A": {"name":"主動野村臺灣優選","issuer":"野村投信","type":"active","subtype":"台股成長","link":"https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00980A&tab=Shareholding"},
    "00981A": {"name":"主動統一台股增長","issuer":"統一投信","type":"active","subtype":"台股成長","link":"https://www.uni-fund.com.tw/etf/00981a"},
    "00982A": {"name":"主動群益台灣強棒","issuer":"群益投信","type":"active","subtype":"台股攻守","link":"https://www.capitalfund.com.tw/etf/00982a"},
    "00983A": {"name":"主動中信ARK創新","issuer":"中信投信","type":"active","subtype":"海外科技","link":"https://www.ctitrust.com.tw/product/etf/00983a"},
    "00984A": {"name":"主動安聯台灣高息","issuer":"安聯投信","type":"active","subtype":"台股高息成長","link":"https://www.allianzgi.com.tw/etf/00984a"},
    "00985A": {"name":"主動野村台灣50","issuer":"野村投信","type":"active","subtype":"台股市值型","link":"https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00985A&tab=Shareholding"},
    "00986A": {"name":"主動台新龍頭成長","issuer":"台新投信","type":"active","subtype":"海外科技","link":"https://www.taishinetf.com.tw/etf/00986a"},
    "00987A": {"name":"主動台新優勢成長","issuer":"台新投信","type":"active","subtype":"台股成長","link":"https://www.taishinetf.com.tw/etf/00987a"},
    "00988A": {"name":"主動統一全球創新","issuer":"統一投信","type":"active","subtype":"海外科技","link":"https://www.uni-fund.com.tw/etf/00988a"},
    "00989A": {"name":"主動摩根美國科技","issuer":"摩根投信","type":"active","subtype":"海外科技","link":"https://www.jpmorganfunds.com.tw/etf/00989a"},
    "00990A": {"name":"主動元大AI新經濟","issuer":"元大投信","type":"active","subtype":"海外AI","link":"https://www.yuantaetfs.com/product/detail/00990a"},
    "00991A": {"name":"主動復華未來50","issuer":"復華投信","type":"active","subtype":"台股成長","link":"https://www.fhtrust.com.tw/etf/00991a"},
    "00992A": {"name":"主動群益科技創新","issuer":"群益投信","type":"active","subtype":"台股科技","link":"https://www.capitalfund.com.tw/etf/00992a"},
    "00993A": {"name":"主動安聯台灣","issuer":"安聯投信","type":"active","subtype":"台股均衡","link":"https://www.allianzgi.com.tw/etf/00993a"},
    "00994A": {"name":"主動第一金台股優","issuer":"第一金投信","type":"active","subtype":"台股成長","link":"https://www.firsttrust.com.tw/etf/00994a"},
    "00995A": {"name":"主動中信台灣卓越","issuer":"中信投信","type":"active","subtype":"台股成長","link":"https://www.ctitrust.com.tw/product/etf/00995a"},
    "00996A": {"name":"主動兆豐台灣豐收","issuer":"兆豐投信","type":"active","subtype":"台股均衡","link":"https://www.chailease.com.tw/etf/00996a"},
    "00997A": {"name":"主動群益美國增長","issuer":"群益投信","type":"active","subtype":"海外成長","link":"https://www.capitalfund.com.tw/etf/00997a"},
    "00998A": {"name":"主動復華金融股息","issuer":"復華投信","type":"active","subtype":"台股金融","link":"https://www.fhtrust.com.tw/etf/00998a"},
    "00400A": {"name":"主動國泰動能高息","issuer":"國泰投信","type":"active","subtype":"台股高息","link":"https://www.cathaysite.com.tw/etf/00400a"},
    "00401A": {"name":"主動摩根台灣鑫收","issuer":"摩根投信","type":"active","subtype":"台股配息","link":"https://www.jpmorganfunds.com.tw/etf/00401a"},
    "00403A": {"name":"主動統一台股升級50","issuer":"統一投信","type":"active","subtype":"台股市值型","link":"https://www.uni-fund.com.tw/etf/00403a"},
    "0050":   {"name":"元大台灣50","issuer":"元大投信","type":"passive","subtype":"市值型","link":"https://www.yuantaetfs.com/product/detail/0050"},
    "0056":   {"name":"元大高股息","issuer":"元大投信","type":"passive","subtype":"高股息","link":"https://www.yuantaetfs.com/product/detail/0056"},
    "00878":  {"name":"國泰永續高股息","issuer":"國泰投信","type":"passive","subtype":"ESG高股息","link":"https://www.cathaysite.com.tw/etf/00878"},
    "00919":  {"name":"群益台灣精選高息","issuer":"群益投信","type":"passive","subtype":"高股息","link":"https://www.capitalfund.com.tw/etf/00919"},
    "00929":  {"name":"復華台灣科技優息","issuer":"復華投信","type":"passive","subtype":"科技高息","link":"https://www.fhtrust.com.tw/etf/00929"},
    "00713":  {"name":"元大台灣高息低波","issuer":"元大投信","type":"passive","subtype":"高息低波","link":"https://www.yuantaetfs.com/product/detail/00713"},
    "006208": {"name":"富邦台50","issuer":"富邦投信","type":"passive","subtype":"市值型","link":"https://www.fubon.com/etf/006208"},
    "00692":  {"name":"富邦公司治理","issuer":"富邦投信","type":"passive","subtype":"ESG","link":"https://www.fubon.com/etf/00692"},
    "00881":  {"name":"國泰台灣5G+","issuer":"國泰投信","type":"passive","subtype":"科技主題","link":"https://www.cathaysite.com.tw/etf/00881"},
    "00891":  {"name":"中信關鍵半導體","issuer":"中信投信","type":"passive","subtype":"半導體","link":"https://www.ctitrust.com.tw/product/etf/00891"},
    "00893":  {"name":"國泰智能電動車","issuer":"國泰投信","type":"passive","subtype":"電動車","link":"https://www.cathaysite.com.tw/etf/00893"},
    "00900":  {"name":"富邦特選高股息30","issuer":"富邦投信","type":"passive","subtype":"高股息","link":"https://www.fubon.com/etf/00900"},
    "00905":  {"name":"FT臺灣Smart","issuer":"復華投信","type":"passive","subtype":"Smart Beta","link":"https://www.fhtrust.com.tw/etf/00905"},
    "00935":  {"name":"野村臺灣新科技50","issuer":"野村投信","type":"passive","subtype":"科技成長","link":"https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00935"},
    "00947":  {"name":"台新臺灣IC設計","issuer":"台新投信","type":"passive","subtype":"IC設計","link":"https://www.taishinetf.com.tw/etf/00947"},
}

FALLBACK_DATA = {
    "00980A": {"2330":6.8,"2317":5.1,"2454":5.0,"2357":4.3,"2881":3.9,"3661":3.5,"2382":3.2,"6669":3.1,"3008":2.9,"4938":2.7},
    "00981A": {"2330":8.5,"2454":6.2,"2317":5.8,"6669":5.1,"3661":4.9,"3008":4.2,"2382":3.9,"4938":3.5,"6005":3.3,"2395":3.1},
    "00982A": {"2330":7.2,"2454":5.5,"2317":5.0,"2308":4.1,"2382":3.8,"6669":3.5,"2395":3.2,"3661":3.0,"3008":2.8,"4938":2.6},
    "00983A": {"TSLA":12.5,"PLTR":8.3,"HOOD":6.2,"SHOP":5.8,"COIN":4.5,"ROKU":4.1,"ZM":3.8,"TWLO":3.5},
    "00984A": {"2330":5.5,"2317":4.8,"2454":4.5,"6669":3.8,"2882":3.5,"5880":3.2,"2881":3.0,"2886":2.8,"2892":2.6,"5876":2.5},
    "00985A": {"2330":28.5,"2454":6.8,"2317":5.2,"2308":3.9,"2382":3.5,"2303":3.2,"3661":2.8,"6669":2.5,"2395":2.2,"3034":2.0},
    "00986A": {"GOOGL":9.5,"NVDA":8.8,"AVGO":7.5,"2330":6.8,"GS":5.5,"META":5.2,"MSFT":4.8,"AMZN":4.5},
    "00987A": {"2330":9.2,"2454":7.1,"2317":5.9,"6669":5.2,"3661":4.8,"3008":4.3,"2382":3.9,"4938":3.5},
    "00988A": {"MU":9.8,"GOOGL":8.5,"AVGO":7.8,"NVDA":6.2,"AMD":5.5,"MSFT":5.0,"2330":4.8},
    "00989A": {"NVDA":11.5,"GOOGL":9.8,"LRCX":7.2,"2330":5.8,"META":5.5,"MSFT":5.2},
    "00990A": {"2330":8.5,"GOOGL":7.8,"NVDA":7.5,"AVGO":6.8,"MSFT":6.2,"TSM":5.5},
    "00991A": {"2330":20.3,"2454":8.5,"2317":6.2,"6669":5.5,"3661":5.0,"2395":4.5,"4938":4.2,"3008":3.8,"2382":3.5},
    "00992A": {"2330":12.5,"2454":9.2,"6669":7.5,"3661":6.8,"3008":5.5,"4938":5.0,"2395":4.5,"2382":4.2},
    "00993A": {"2330":10.5,"2454":6.5,"2317":5.8,"2308":4.5,"6669":4.0,"3661":3.5,"2382":3.2,"2395":3.0},
    "00994A": {"2330":12.8,"2454":8.5,"6669":6.5,"3661":5.8,"4938":5.2,"3008":4.8,"2382":4.5,"2395":4.0},
    "00995A": {"2330":15.2,"2454":9.2,"6669":6.8,"3661":5.5,"4938":4.8,"3008":4.5,"2382":4.0,"2395":3.5},
    "00996A": {"2330":11.5,"2454":7.2,"2317":5.5,"6669":4.8,"3661":4.3,"2382":3.9,"2395":3.5,"4938":3.2},
    "00997A": {"NVDA":10.5,"MSFT":9.8,"AAPL":8.5,"GOOGL":8.0,"AMZN":7.5,"META":6.8},
    "00998A": {"2882":12.5,"5880":11.8,"2886":10.5,"2881":9.8,"2892":9.2,"5876":8.5,"2303":7.8},
    "00400A": {"2330":8.5,"2317":5.5,"2454":5.0,"2882":4.5,"5880":4.2,"2886":3.9,"2881":3.5,"5876":3.2},
    "00401A": {"2330":9.2,"2454":6.5,"2317":5.8,"6669":4.5,"3661":4.0,"2382":3.5,"2882":3.2,"5880":3.0},
    "00403A": {"2330":28.0,"2454":8.8,"2317":6.5,"2308":4.5,"2382":3.8,"2303":3.5,"3661":3.2,"6669":2.9,"2395":2.5,"3034":2.2},
    "0050":   {"2330":49.5,"2454":6.2,"2317":4.8,"2308":3.5,"2382":3.0,"2303":2.8,"3661":2.5,"6669":2.2,"2395":2.0,"3034":1.8,"2412":1.7,"2882":1.6,"2886":1.5,"2881":1.4,"5880":1.3,"2892":1.2,"2357":1.1,"2376":1.0,"2301":0.9,"1303":0.8},
    "0056":   {"2882":8.2,"5880":7.8,"2303":6.5,"2886":6.2,"2881":5.8,"5876":5.5,"2892":5.0,"2330":4.8,"3034":4.2,"2308":3.9,"2317":3.5,"2376":3.2,"2301":2.8,"2474":2.5,"1590":2.2},
    "00878":  {"2303":6.8,"5880":6.5,"2330":6.2,"2882":5.8,"2886":5.5,"5876":5.0,"2892":4.8,"2308":4.5,"2881":4.2,"2317":3.8,"2376":3.2,"2382":2.8,"2301":2.5,"1590":2.2},
    "00919":  {"2330":8.5,"2317":6.2,"2454":5.8,"2382":4.5,"6669":4.0,"3661":3.5,"2308":3.2,"2395":2.8,"2303":2.5,"5880":2.2,"2882":2.0,"2886":1.8},
    "00929":  {"2330":12.5,"2454":8.5,"2317":6.8,"6669":5.5,"3661":5.0,"3008":4.5,"2382":4.0,"4938":3.5,"2395":3.0,"6005":2.8},
    "00713":  {"4904":9.8,"2882":8.5,"5880":7.8,"2886":7.2,"2881":6.8,"5876":6.5,"2892":5.8,"1216":5.2,"2303":4.8,"2002":4.5},
    "006208": {"2330":49.5,"2454":6.2,"2317":4.8,"2308":3.5,"2382":3.0,"2303":2.8,"3661":2.5,"6669":2.2,"2395":2.0,"3034":1.8},
    "00692":  {"2330":35.2,"2454":5.8,"2317":4.5,"2308":3.8,"2382":3.2,"2412":2.8,"2303":2.5,"3661":2.2,"6669":2.0,"2395":1.8},
    "00881":  {"2330":12.5,"2454":9.8,"2317":7.5,"6669":6.8,"3661":5.5,"3008":4.5,"2395":4.0,"4938":3.5,"2382":3.2,"2412":3.0},
    "00891":  {"2330":25.5,"2454":12.8,"6669":8.5,"3661":6.8,"4938":5.5,"3034":5.0,"3008":4.5,"2395":4.0,"2379":3.5,"6176":3.0},
    "00893":  {"2330":8.5,"6669":7.5,"3661":6.8,"3008":6.0,"4938":5.5,"2395":4.8,"2382":4.2,"6005":3.8},
    "00900":  {"2330":8.5,"2303":6.8,"2317":5.5,"5880":5.2,"2882":5.0,"2886":4.8,"2881":4.5,"5876":4.2,"2892":3.8,"2308":3.5},
    "00905":  {"2330":15.5,"2454":8.2,"2317":5.8,"6669":5.0,"3661":4.5,"2395":3.8,"4938":3.5,"3008":3.2,"2382":3.0,"2308":2.8},
    "00935":  {"2330":18.5,"2454":10.2,"6669":7.8,"3661":6.5,"4938":5.5,"3008":5.0,"2395":4.5,"2382":4.0,"6005":3.5,"3034":3.2},
    "00947":  {"2454":18.5,"6669":12.8,"3661":10.5,"4938":8.2,"3034":6.8,"2379":5.5,"6176":4.8,"3231":4.2,"2344":3.8,"2327":3.5},
}

def fetch_from_moneydj(etf_code):
    """從 MoneyDJ 抓取 ETF 持股資料"""
    url = f"https://www.moneydj.com/ETF/X/Basic/Basic0007a.xdjhtm?etfid={etf_code}.TW"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Referer": "https://www.moneydj.com/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        if resp.status_code != 200:
            return {}
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        holdings = {}
        # MoneyDJ 的持股表格
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    # 嘗試找股票代號（4~6位數字）
                    code_text = cols[0].get_text(strip=True)
                    weight_text = cols[2].get_text(strip=True).replace("%", "").replace(",", "").strip()
                    code_match = re.search(r'\((\d{4,6})\)', code_text)
                    if not code_match:
                        code_match = re.match(r'^(\d{4,6})$', code_text)
                    if code_match and weight_text:
                        try:
                            code = code_match.group(1)
                            weight = float(weight_text)
                            if 0 < weight < 100:
                                holdings[code] = weight
                        except:
                            pass
        if holdings:
            logging.info(f"✅ MoneyDJ {etf_code} 成功抓取 {len(holdings)} 筆")
            return holdings
    except Exception as e:
        logging.warning(f"⚠️ MoneyDJ {etf_code} 失敗：{e}")
    return {}

def update_all_holdings():
    """更新所有 ETF 持股資料"""
    global holdings_cache, last_updated
    logging.info("🔄 開始更新持股資料...")
    new_cache = {}
    success_count = 0

    for etf_code, meta in ETF_META.items():
        # 先嘗試從 MoneyDJ 抓取（主要來源）
        holdings = fetch_from_moneydj(etf_code)

        # 抓取失敗就用備用資料
        if not holdings:
            holdings = FALLBACK_DATA.get(etf_code, {})
            source = "fallback"
        else:
            source = "moneydj"
            success_count += 1

        new_cache[etf_code] = {
            "code": etf_code,
            "name": meta["name"],
            "issuer": meta["issuer"],
            "type": meta["type"],
            "subtype": meta.get("subtype", ""),
            "link": meta.get("link", ""),
            "holdings": holdings,
            "source": source,
        }
        time.sleep(0.8)  # 避免太頻繁

    holdings_cache = new_cache
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    logging.info(f"✅ 更新完成：{last_updated}，MoneyDJ 成功 {success_count}/{len(ETF_META)} 支")

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "台股 ETF 持股查詢 API",
        "last_updated": last_updated,
        "etf_count": len(holdings_cache)
    })

@app.route("/api/holdings")
def get_all_holdings():
    try:
        if not holdings_cache:
            update_all_holdings()
        return jsonify({
            "last_updated": last_updated,
            "etf_count": len(holdings_cache),
            "etfs": holdings_cache
        })
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<stock_code>")
def get_etfs_by_stock(stock_code):
    try:
        if not holdings_cache:
            update_all_holdings()
        result = []
        code = stock_code.upper().strip()
        for etf_code, etf_data in holdings_cache.items():
            weight = etf_data["holdings"].get(code) or etf_data["holdings"].get(stock_code)
            if weight is not None:
                result.append({
                    "etfCode": etf_code,
                    "etfName": etf_data.get("name", ""),
                    "issuer": etf_data.get("issuer", ""),
                    "type": etf_data.get("type", ""),
                    "subtype": etf_data.get("subtype", ""),
                    "link": etf_data.get("link", ""),
                    "weight": weight,
                    "source": etf_data.get("source", ""),
                })
        result.sort(key=lambda x: x["weight"], reverse=True)
        return jsonify({
            "stockCode": stock_code,
            "last_updated": last_updated,
            "count": len(result),
            "etfs": result
        })
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# 每天 9:30 自動更新
scheduler = BackgroundScheduler()
scheduler.add_job(update_all_holdings, "cron", hour=9, minute=30)
scheduler.start()

# 啟動時立即更新
update_all_holdings()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
