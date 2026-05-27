from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import time
import logging
import traceback
from datetime import datetime

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# 全域快取
holdings_cache = {}
last_updated = None

# 備用靜態資料（當爬蟲失敗時使用）
FALLBACK_DATA = {
    "00980A": {"2330":6.8,"2317":5.1,"2454":5.0,"2357":4.3,"2881":3.9,"3661":3.5,"2382":3.2,"6669":3.1,"3008":2.9,"4938":2.7},
    "00981A": {"2330":8.5,"2454":6.2,"2317":5.8,"6669":5.1,"3661":4.9,"3008":4.2,"2382":3.9,"4938":3.5,"6005":3.3,"2395":3.1},
    "00982A": {"2330":7.2,"2454":5.5,"2317":5.0,"2308":4.1,"2382":3.8,"6669":3.5,"2395":3.2,"3661":3.0,"3008":2.8,"4938":2.6},
    "00984A": {"2330":5.5,"2317":4.8,"2454":4.5,"6669":3.8,"2882":3.5,"5880":3.2,"2881":3.0,"2886":2.8,"2892":2.6,"5876":2.5},
    "00985A": {"2330":28.5,"2454":6.8,"2317":5.2,"2308":3.9,"2382":3.5,"2303":3.2,"3661":2.8,"6669":2.5,"2395":2.2,"3034":2.0},
    "00987A": {"2330":9.2,"2454":7.1,"2317":5.9,"6669":5.2,"3661":4.8,"3008":4.3,"2382":3.9,"4938":3.5,"6005":3.2,"2395":2.9},
    "00991A": {"2330":20.3,"2454":8.5,"2317":6.2,"6669":5.5,"3661":5.0,"2395":4.5,"4938":4.2,"3008":3.8,"2382":3.5,"5483":3.2},
    "00992A": {"2330":12.5,"2454":9.2,"6669":7.5,"3661":6.8,"3008":5.5,"4938":5.0,"2395":4.5,"2382":4.2,"6005":3.8,"3034":3.5},
    "00993A": {"2330":10.5,"2454":6.5,"2317":5.8,"2308":4.5,"6669":4.0,"3661":3.5,"2382":3.2,"2395":3.0,"4938":2.8,"3008":2.5},
    "00994A": {"2330":12.8,"2454":8.5,"6669":6.5,"3661":5.8,"4938":5.2,"3008":4.8,"2382":4.5,"2395":4.0,"6005":3.5,"3034":3.2},
    "00995A": {"2330":15.2,"2454":9.2,"6669":6.8,"3661":5.5,"4938":4.8,"3008":4.5,"2382":4.0,"2395":3.5,"6005":3.2,"3034":2.9},
    "00996A": {"2330":11.5,"2454":7.2,"2317":5.5,"6669":4.8,"3661":4.3,"2382":3.9,"2395":3.5,"4938":3.2,"3008":2.9,"2308":2.6},
    "00400A": {"2330":8.5,"2317":5.5,"2454":5.0,"2882":4.5,"5880":4.2,"2886":3.9,"2881":3.5,"5876":3.2,"2892":3.0,"2303":2.7},
    "00401A": {"2330":9.2,"2454":6.5,"2317":5.8,"6669":4.5,"3661":4.0,"2382":3.5,"2882":3.2,"5880":3.0,"2886":2.8,"2881":2.6},
    "00986A": {"GOOGL":9.5,"NVDA":8.8,"AVGO":7.5,"2330":6.8,"GS":5.5,"META":5.2,"MSFT":4.8,"AMZN":4.5,"AAPL":4.2,"TSM":3.9},
    "00988A": {"MU":9.8,"GOOGL":8.5,"AVGO":7.8,"LITE":6.5,"NVDA":6.2,"AMD":5.5,"MSFT":5.0,"2330":4.8,"MRVL":4.3,"AMAT":3.9},
    "00989A": {"NVDA":11.5,"GOOGL":9.8,"LRCX":7.2,"TTWO":6.5,"2330":5.8,"META":5.5,"MSFT":5.2,"AMZN":4.8,"AAPL":4.5,"AMD":4.2},
    "00990A": {"2330":8.5,"GOOGL":7.8,"NVDA":7.5,"AVGO":6.8,"MSFT":6.2,"TSM":5.5,"AMD":5.0,"META":4.8,"AMZN":4.5,"AAPL":4.2},
    "00991A": {"2330":20.3,"2454":8.5,"2317":6.2,"6669":5.5,"3661":5.0,"2395":4.5,"4938":4.2,"3008":3.8,"2382":3.5,"5483":3.2},
    "00997A": {"NVDA":10.5,"MSFT":9.8,"AAPL":8.5,"GOOGL":8.0,"AMZN":7.5,"META":6.8,"AVGO":5.5,"AMD":5.0,"TSLA":4.5,"TSM":4.0},
    "00998A": {"2882":12.5,"5880":11.8,"2886":10.5,"2881":9.8,"2892":9.2,"5876":8.5,"2303":7.8,"2884":6.5,"2885":5.8,"2887":5.2},
    "0050":   {"2330":49.5,"2454":6.2,"2317":4.8,"2308":3.5,"2382":3.0,"2303":2.8,"3661":2.5,"6669":2.2,"2395":2.0,"3034":1.8,"2412":1.7,"2882":1.6,"2886":1.5,"2881":1.4,"5880":1.3,"2892":1.2,"2357":1.1,"2376":1.0,"2301":0.9,"1303":0.8},
    "0056":   {"2882":8.2,"5880":7.8,"2303":6.5,"2886":6.2,"2881":5.8,"5876":5.5,"2892":5.0,"2330":4.8,"3034":4.2,"2308":3.9,"2317":3.5,"2376":3.2,"2301":2.8,"2474":2.5,"1590":2.2,"2344":2.0,"2395":1.8,"2379":1.6,"2002":1.4,"1216":1.2},
    "00878":  {"2303":6.8,"5880":6.5,"2330":6.2,"2882":5.8,"2886":5.5,"5876":5.0,"2892":4.8,"2308":4.5,"2881":4.2,"2317":3.8,"2376":3.2,"2382":2.8,"2301":2.5,"1590":2.2,"2344":2.0,"3034":1.8,"2395":1.6,"2474":1.4,"2379":1.2,"1216":1.0},
    "00919":  {"2330":8.5,"2317":6.2,"2454":5.8,"2382":4.5,"6669":4.0,"3661":3.5,"2308":3.2,"2395":2.8,"2303":2.5,"5880":2.2,"2882":2.0,"2886":1.8,"5876":1.6,"2892":1.4,"2301":1.2},
    "00929":  {"2330":12.5,"2454":8.5,"2317":6.8,"6669":5.5,"3661":5.0,"3008":4.5,"2382":4.0,"4938":3.5,"2395":3.0,"6005":2.8,"3034":2.5,"2379":2.2,"2308":2.0,"2301":1.8,"6176":1.5},
    "00713":  {"4904":9.8,"2882":8.5,"5880":7.8,"2886":7.2,"2881":6.8,"5876":6.5,"2892":5.8,"1216":5.2,"2303":4.8,"2002":4.5,"1301":3.8,"1303":3.5,"2207":3.2,"2301":2.8,"2376":2.5},
    "006208": {"2330":49.5,"2454":6.2,"2317":4.8,"2308":3.5,"2382":3.0,"2303":2.8,"3661":2.5,"6669":2.2,"2395":2.0,"3034":1.8,"2412":1.7,"2882":1.6,"2886":1.5,"2881":1.4,"5880":1.3},
    "00692":  {"2330":35.2,"2454":5.8,"2317":4.5,"2308":3.8,"2382":3.2,"2412":2.8,"2303":2.5,"3661":2.2,"6669":2.0,"2395":1.8,"2882":1.6,"2886":1.4,"2881":1.2,"5880":1.0,"2892":0.9},
    "00881":  {"2330":12.5,"2454":9.8,"2317":7.5,"6669":6.8,"3661":5.5,"3008":4.5,"2395":4.0,"4938":3.5,"2382":3.2,"2412":3.0,"3034":2.5,"2379":2.2,"6176":2.0,"1590":1.8,"6005":1.5},
    "00891":  {"2330":25.5,"2454":12.8,"6669":8.5,"3661":6.8,"4938":5.5,"3034":5.0,"3008":4.5,"2395":4.0,"2379":3.5,"6176":3.0,"3231":2.5,"2344":2.2,"2327":2.0,"2303":1.8,"2474":1.5},
    "00893":  {"2330":8.5,"6669":7.5,"3661":6.8,"3008":6.0,"4938":5.5,"2395":4.8,"2382":4.2,"6005":3.8,"3034":3.2,"2379":2.8},
    "00900":  {"2330":8.5,"2303":6.8,"2317":5.5,"5880":5.2,"2882":5.0,"2886":4.8,"2881":4.5,"5876":4.2,"2892":3.8,"2308":3.5,"2382":3.0,"2376":2.5,"2301":2.2,"2474":2.0,"1590":1.8},
    "00935":  {"2330":18.5,"2454":10.2,"6669":7.8,"3661":6.5,"4938":5.5,"3008":5.0,"2395":4.5,"2382":4.0,"6005":3.5,"3034":3.2,"2379":2.8,"6176":2.5,"1590":2.2,"3231":2.0,"2344":1.8},
    "00947":  {"2454":18.5,"6669":12.8,"3661":10.5,"4938":8.2,"3034":6.8,"2379":5.5,"6176":4.8,"3231":4.2,"2344":3.8,"2327":3.5},
}

ETF_META = {
    "00980A": {"name":"主動野村臺灣優選","issuer":"野村投信","type":"active","subtype":"台股成長","link":"https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00980A&tab=Shareholding"},
    "00981A": {"name":"主動統一台股增長","issuer":"統一投信","type":"active","subtype":"台股成長","link":"https://www.uni-fund.com.tw/etf/00981a"},
    "00982A": {"name":"主動群益台灣強棒","issuer":"群益投信","type":"active","subtype":"台股攻守","link":"https://www.capitalfund.com.tw/etf/00982a"},
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
    "00400A": {"name":"主動國泰動能高息","issuer":"國泰投信","type":"active","subtype":"台股高息","link":"https://www.cathaysite.com.tw/etf/00400a"},
    "00401A": {"name":"主動摩根台灣鑫收","issuer":"摩根投信","type":"active","subtype":"台股配息","link":"https://www.jpmorganfunds.com.tw/etf/00401a"},
    "00997A": {"name":"主動群益美國增長","issuer":"群益投信","type":"active","subtype":"海外成長","link":"https://www.capitalfund.com.tw/etf/00997a"},
    "00998A": {"name":"主動復華金融股息","issuer":"復華投信","type":"active","subtype":"台股金融","link":"https://www.fhtrust.com.tw/etf/00998a"},
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
    "00935":  {"name":"野村臺灣新科技50","issuer":"野村投信","type":"passive","subtype":"科技成長","link":"https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00935"},
    "00947":  {"name":"台新臺灣IC設計","issuer":"台新投信","type":"passive","subtype":"IC設計","link":"https://www.taishinetf.com.tw/etf/00947"},
}

def load_fallback_cache():
    """直接用靜態備用資料建立快取"""
    global holdings_cache, last_updated
    new_cache = {}
    for etf_code, holdings in FALLBACK_DATA.items():
        meta = ETF_META.get(etf_code, {})
        new_cache[etf_code] = {
            "code": etf_code,
            "name": meta.get("name", etf_code),
            "issuer": meta.get("issuer", ""),
            "type": meta.get("type", "passive"),
            "subtype": meta.get("subtype", ""),
            "link": meta.get("link", ""),
            "holdings": holdings,
            "source": "fallback"
        }
    holdings_cache = new_cache
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    logging.info(f"✅ 備用資料載入完成，共 {len(holdings_cache)} 支 ETF")

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
            load_fallback_cache()
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
            load_fallback_cache()
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

# 啟動時立即載入資料
load_fallback_cache()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
