import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, send_from_directory
import concurrent.futures
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# ---------- تنظیمات ----------
MAX_HISTORY = 60          # ۶۰ دقیقه
HTTP_TIMEOUT = 2          # ثانیه
MAX_WORKERS = 10
# -----------------------------

# سرویس‌های داخلی (ایرانی)
INTERNAL_HOSTS = [
    {"name": "آپارات", "host": "https://www.aparat.com"},
    {"name": "دیجی کالا", "host": "https://www.digikala.com"},
    {"name": "دیوار", "host": "https://divar.ir"},
    {"name": "اسنپ", "host": "https://snapp.ir"},
    {"name": "ترب", "host": "https://torob.com"},
    {"name": "دیجیاتو", "host": "https://digiato.com"},
    {"name": "ایرنیک", "host": "https://new.nic.ir"}
]

# سرویس‌های خارجی
EXTERNAL_HOSTS = [
    {"name": "Amazon", "host": "https://www.amazon.com"},
    {"name": "App Store", "host": "https://apps.apple.com"},
    {"name": "ChatGPT", "host": "https://chat.openai.com"},
    {"name": "Cloudflare", "host": "https://www.cloudflare.com"},
    {"name": "Cloudflare DNS", "host": "https://1.1.1.1"},
    {"name": "Deepseek", "host": "https://www.deepseek.com"},
    {"name": "Docker Hub", "host": "https://hub.docker.com"},
    {"name": "Github", "host": "https://github.com"},
    {"name": "Gitlab", "host": "https://gitlab.com"},
    {"name": "Google DNS", "host": "https://8.8.8.8"},
    {"name": "Letsencrypt", "host": "https://letsencrypt.org"},
    {"name": "PlayStation", "host": "https://www.playstation.com"},
    {"name": "PyPi", "host": "https://pypi.org"},
    {"name": "Qwen ai", "host": "https://qwen.ai"},
    {"name": "Spotify", "host": "https://open.spotify.com"},
    {"name": "Steam", "host": "https://store.steampowered.com"},
    {"name": "Wordpress", "host": "https://wordpress.org"},
    {"name": "Z ai", "host": "https://z.ai"}
]
GOOGLE_HOSTS = [
    {"name": "Google Search", "host": "https://www.google.com"},
    {"name": "Google News", "host": "https://news.google.com"},
    {"name": "Google Scholar", "host": "https://scholar.google.com"},
    {"name": "Google Maps", "host": "https://www.google.com/maps"},
    {"name": "Gmail", "host": "https://www.google.com/mail"},
    {"name": "Google Drive", "host": "https://drive.google.com"},
    {"name": "Google Docs", "host": "https://www.google.com/docs"},
    {"name": "Google Sheets", "host": "https://sheets.google.com"},
    {"name": "Google Slides", "host": "https://slides.google.com"},
    {"name": "Google Meet", "host": "https://meet.google.com"},
    {"name": "Google Fonts", "host": "https://fonts.google.com"},
    {"name": "Google translate", "host": "https://translate.google.com"},
    {"name": "Google Play", "host": "https://play.google.com/store"},
    {"name": "Gemini", "host": "https://gemini.google.com"}
]
ALL_HOSTS = INTERNAL_HOSTS + EXTERNAL_HOSTS + GOOGLE_HOSTS

# هدرهای مرورگر واقعی
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fa,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

data_lock = threading.RLock()
status_data = {}

def create_session():
    session = requests.Session()
    retry = Retry(total=1, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update(BROWSER_HEADERS)
    return session

def init_host_data():
    for entry in ALL_HOSTS:
        name = entry["name"]
        status_data[name] = {
            "host": entry["host"],
            "current": {"success": None, "delay": None, "time": None, "status_code": None},
            "history": [None] * MAX_HISTORY
        }

def check_http(host):
    session = create_session()
    start = time.time()
    try:
        resp = session.head(host, timeout=HTTP_TIMEOUT, allow_redirects=True)
        if resp.status_code >= 400:
            resp = session.get(host, timeout=HTTP_TIMEOUT, allow_redirects=True, stream=True)
            resp.close()
        success = resp.status_code < 400
        status_code = resp.status_code
    except Exception:
        success = False
        status_code = None
    delay = round((time.time() - start) * 1000, 2) if success else None
    return {"success": success, "delay": delay, "status_code": status_code}

def ping_host(entry):
    result = check_http(entry["host"])
    result["time"] = datetime.now().strftime("%H:%M:%S")
    return result

def update_all_hosts():
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_entry = {executor.submit(ping_host, entry): entry for entry in ALL_HOSTS}
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                result = future.result()
            except Exception:
                result = {"success": False, "delay": None, "status_code": None, "time": datetime.now().strftime("%H:%M:%S")}
            name = entry["name"]
            with data_lock:
                status_data[name]["current"] = result
                history = status_data[name]["history"]
                history.pop(0)
                history.append(1 if result["success"] else 0)

def wait_until_next_minute():
    now = datetime.now()
    next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    return max(0, (next_minute - now).total_seconds())

def background_loop():
    while True:
        time.sleep(wait_until_next_minute())
        start_time = time.time()
        update_all_hosts()
        elapsed = time.time() - start_time
        print(f"[{datetime.now().strftime('%H:%M:%S')}] update done : (Time: {elapsed:.2f}s)")

init_host_data()
update_all_hosts()
thread = threading.Thread(target=background_loop, daemon=True)
thread.start()

# ---------- قالب HTML با طراحی کاملاً واکنش‌گرا ----------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>پایش سرویس‌ها</title>

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

         @font-face {
            font-family: 'Vazir';
            src: url('/Vazir-Bold-FD.ttf') format('truetype');
            font-weight: 500;
            font-style: normal;
            font-display: swap;
            unicode-range: U+0020-0040, U+005B-0060, U+007B-FFFF;
        }

         @font-face {
            font-family: 'English';
            src: url('/Arcane Nine.otf') format('truetype');
            font-weight: 500;
            font-style: normal;
            font-display: swap;
            unicode-range: U+0041-005A, U+0061-007A;
        }

        body {
            font-family: 'Vazir', 'English', Tahoma, sans-serif;
            background: #f5f7fb;
            padding: 16px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            color: #1e293b;
        }

        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }

        /* ----- هدر ----- */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 24px;
        }

        .header h1 {
            font-size: clamp(1.5rem, 5vw, 2rem);
            font-weight: 700;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .last-update {
            background: white;
            padding: 8px 16px;
            border-radius: 100px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .refresh-btn {
            background: white;
            border: none;
            width: 42px;
            height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
            transition: all 0.2s;
            color: #2563eb;
            font-size: 1.3rem;
        }

        .refresh-btn:hover {
            background: #2563eb;
            color: white;
            transform: rotate(30deg);
        }

        .refresh-btn.loading {
            pointer-events: none;
            opacity: 0.7;
        }

        .refresh-btn.loading i {
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* ----- کارت آمار کلی ----- */
        .stats-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }

        .stat-card {
            background: white;
            padding: 18px 16px;
            border-radius: 24px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.02);
            display: flex;
            align-items: center;
            gap: 14px;
            transition: transform 0.2s;
            border: 1px solid rgba(0,0,0,0.02);
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 18px;
            background: #eef2ff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
        }

        .stat-content h3 {
            font-size: 0.9rem;
            font-weight: 500;
            color: #64748b;
            margin-bottom: 4px;
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
        }

        /* ----- بخش گروه ----- */
        .group-section {
            margin-bottom: 40px;
        }

        .group-header {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 20px;
        }

        .group-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .group-progress {
            flex: 1;
            min-width: 200px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .progress-bar-container {
            height: 8px;
            background: #e2e8f0;
            border-radius: 20px;
            flex: 1;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            width: 0%;
            background: #10b981;
            border-radius: 20px;
            transition: width 0.5s ease;
        }

        .group-percent {
            font-weight: 700;
            min-width: 60px;
            text-align: left;
            font-size: 1rem;
        }

        .service-count {
            background: #e2e8f0;
            padding: 4px 12px;
            border-radius: 40px;
            font-size: 0.9rem;
            color: #475569;
        }

        /* ----- جدول سرویس‌ها (کارتی) ----- */
        .services-table-container {
            background: white;
            border-radius: 28px;
            padding: 8px 0;
            box-shadow: 0 10px 30px -5px rgba(0,0,0,0.03);
            border: 1px solid rgba(0,0,0,0.03);
            overflow-x: auto;
        }

        .services-table {
            width: 100%;
            border-collapse: collapse;
            min-width: 900px;
        }

        .services-table th {
            text-align: right;
            padding: 18px 16px;
            font-weight: 600;
            font-size: 0.85rem;
            color: #64748b;
            border-bottom: 1px solid #f1f5f9;
            white-space: nowrap;
        }

        .services-table td {
            padding: 14px 16px;
            border-bottom: 1px solid #f8fafc;
            vertical-align: middle;
        }

        .services-table tbody tr {
            transition: background 0.2s;
        }

        .services-table tbody tr:hover {
            background: #e9e9e9;
        }

        .service-name-cell {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #cbd5e1;
            display: inline-block;
            transition: background 0.3s;
        }

        .status-indicator.up { background: #10b981; box-shadow: 0 0 0 3px #10b98120; }
        .status-indicator.down { background: #ef4444; box-shadow: 0 0 0 3px #ef444420; }
        .status-indicator.pending { background: #f59e0b; }

        .service-name {
            font-weight: 600;
            color: #0f172a;
        }

        .host-badge {
            background: #f1f5f9;
            padding: 4px 10px;
            border-radius: 40px;
            font-size: 0.75rem;
            color: #475569;
            direction: ltr;
            display: inline-block;
            max-width: 180px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 40px;
            font-size: 0.8rem;
            font-weight: 500;
            background: #f1f5f9;
            color: #334155;
        }

        .status-badge.up {
            background: #d1fae5;
            color: #065f46;
        }

        .status-badge.down {
            background: #fee2e2;
            color: #991b1b;
        }

        .delay {
            font-family: monospace;
            background: #f8fafc;
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 0.8rem;
        }

        .uptime-cell {
            font-weight: 600;
        }

        .uptime-badge {
            padding: 4px 8px;
            border-radius: 20px;
            background: #f1f5f9;
            font-size: 0.8rem;
        }

        .sparkline {
            display: flex;
            flex-direction: row-reverse;
            gap: 2px;
            align-items: center;
        }

        .spark-bar {
            width: 4px;
            height: 16px;
            background: #cbd5e1;
            border-radius: 4px;
            transition: background 0.2s;
        }

        .spark-bar.up { background: #10b981; }
        .spark-bar.down { background: #ef4444; }

        /* Skeleton Loading */
        .skeleton-row td {
            position: relative;
        }

        .skeleton {
            background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
            background-size: 200% 100%;
            animation: skeleton-loading 1.5s infinite;
            border-radius: 20px;
            height: 20px;
            width: 80%;
        }

        @keyframes skeleton-loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .skeleton-text {
            height: 16px;
            width: 60%;
        }

        /* انیمیشن به‌روزرسانی ردیف */
        .row-updating {
            animation: row-flash 1s ease-out;
        }

        @keyframes row-flash {
            0% { background: #fef9c3; }
            100% { background: transparent; }
        }

        /* فوتر */
        .footer {
            margin-top: 40px;
            text-align: center;
            color: #64748b;
            font-size: 0.85rem;
        }

        /* ----- انیمیشن‌ها ----- */
        @keyframes pulse-green {
            0% {
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
            }
            70% {
                box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
            }
        }

        @keyframes pulse-red {
            0% {
                box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5);
            }
            70% {
                box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
            }
        }

        /* تعریف نهایی و بدون تکرار */
            .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #cbd5e1;
            display: inline-block;
            transition: background 0.3s;
        }

        .status-indicator.pending {
            background: #f59e0b;
        }
        .services-table tbody tr {
            opacity: 0;
            animation: fadeInRow 0.4s ease forwards;
        }

        .services-table tbody tr:nth-child(1) { animation-delay: 0.03s; }
        .services-table tbody tr:nth-child(2) { animation-delay: 0.06s; }
        .services-table tbody tr:nth-child(3) { animation-delay: 0.09s; }
        .services-table tbody tr:nth-child(4) { animation-delay: 0.12s; }
        .services-table tbody tr:nth-child(5) { animation-delay: 0.15s; }
        /* ادامه به تعداد ردیف‌ها */

        @keyframes fadeInRow {
            from {
                opacity: 0;
                transform: translateY(8px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .stat-card {
            transition: transform 0.2s, box-shadow 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 15px 25px -5px rgba(128, 255, 123, 0.26);
        }


        /////
        

        /* رسپانسیو */
        @media (max-width: 600px) {
            body { padding: 12px; }
            .header h1 { font-size: 1.4rem; }
            .stat-card { padding: 14px; }
            .stat-value { font-size: 1.4rem; }
            .group-title { font-size: 1.2rem; }
            .services-table th, .services-table td { padding: 12px 8px; }
            .host-badge { max-width: 120px; }
        }
    </style>
</head>
<body>
<div class="dashboard">
    <!-- هدر -->
    <div class="header">
        <h1>
            <span>🌐</span> پایش هوشمند
        </h1>
        <div class="header-actions">
            <div class="last-update">
                <span>🕒</span>
                <span id="update-time">--:--:--</span>
            </div>
            <button class="refresh-btn" id="manual-refresh" title="به‌روزرسانی">
                <i>↻</i>
            </button>
        </div>
    </div>

    <!-- کارت‌های خلاصه -->
    <div class="stats-cards">
        <div class="stat-card">
            <div class="stat-icon">🇮🇷</div>
            <div class="stat-content">
                <h3>داخلی</h3>
                <div class="stat-value" id="internal-uptime-stat">—%</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🌍</div>
            <div class="stat-content">
                <h3>خارجی</h3>
                <div class="stat-value" id="external-uptime-stat">—%</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">⚙️</div>
            <div class="stat-content">
                <h3>گوگل</h3>
                <div class="stat-value" id="google-uptime-stat">—%</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-content">
                <h3>کل سرویس‌ها</h3>
                <div class="stat-value" id="total-services">0</div>
            </div>
        </div>
    </div>

    <!-- بخش داخلی -->
    <div class="group-section">
        <div class="group-header">
            <div class="group-title">
                <span>🇮🇷 داخلی</span>
                <span class="service-count">{{ internal_hosts|length }} سرویس</span>
            </div>
            <div class="group-progress">
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" id="internal-progress-fill" style="width: 0%"></div>
                </div>
                <div class="group-percent" id="internal-group-percent">—%</div>
            </div>
        </div>
        <div class="services-table-container">
            <table class="services-table" id="internal-table">
                <thead>
                    <tr>
                        <th>سرویس</th>
                        <th>آدرس</th>
                        <th>وضعیت</th>
                        <th>تاخیر (ms)</th>
                        <th>دسترسی٪</th>
                        <th>آخرین بررسی</th>
                        <th>۶۰ دقیقه اخیر</th>
                    </tr>
                </thead>
                <tbody id="internal-tbody">
                    {% for h in internal_hosts %}
                    <tr data-name="{{ h.name }}" data-host="{{ h.host }}">
                        <td><div class="service-name-cell"><span class="status-indicator pending"></span><span class="service-name">{{ h.name }}</span></div></td>
                        <td><span class="host-badge" title="{{ h.host }}">{{ h.host | replace("https://", "") | replace("http://", "") }}</span></td>
                        <td><span class="status-badge">—</span></td>
                        <td><span class="delay">—</span></td>
                        <td class="uptime-cell"><span class="uptime-badge">—</span></td>
                        <td class="time-cell">—</td>
                        <td><div class="sparkline"></div></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- بخش خارجی -->
    <div class="group-section">
        <div class="group-header">
            <div class="group-title">
                <span>🌍 خارجی</span>
                <span class="service-count">{{ external_hosts|length }} سرویس</span>
            </div>
            <div class="group-progress">
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" id="external-progress-fill" style="width: 0%"></div>
                </div>
                <div class="group-percent" id="external-group-percent">—%</div>
            </div>
        </div>
        <div class="services-table-container">
            <table class="services-table" id="external-table">
                <thead>
                    <tr>
                        <th>سرویس</th>
                        <th>آدرس</th>
                        <th>وضعیت</th>
                        <th>تاخیر (ms)</th>
                        <th>دسترسی٪</th>
                        <th>آخرین بررسی</th>
                        <th>۶۰ دقیقه اخیر</th>
                    </tr>
                </thead>
                <tbody id="external-tbody">
                    {% for h in external_hosts %}
                    <tr data-name="{{ h.name }}" data-host="{{ h.host }}">
                        <td><div class="service-name-cell"><span class="status-indicator pending"></span><span class="service-name">{{ h.name }}</span></div></td>
                        <td><span class="host-badge" title="{{ h.host }}">{{ h.host | replace("https://", "") | replace("http://", "") }}</span></td>
                        <td><span class="status-badge">—</span></td>
                        <td><span class="delay">—</span></td>
                        <td class="uptime-cell"><span class="uptime-badge">—</span></td>
                        <td class="time-cell">—</td>
                        <td><div class="sparkline"></div></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- بخش گوگل -->
    <div class="group-section">
        <div class="group-header">
            <div class="group-title">
                <span>⚙️ گوگل</span>
                <span class="service-count">{{ google_hosts|length }} سرویس</span>
            </div>
            <div class="group-progress">
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" id="google-progress-fill" style="width: 0%"></div>
                </div>
                <div class="group-percent" id="google-group-percent">—%</div>
            </div>
        </div>
        <div class="services-table-container">
            <table class="services-table" id="google-table">
                <thead>
                    <tr>
                        <th>سرویس</th>
                        <th>آدرس</th>
                        <th>وضعیت</th>
                        <th>تاخیر (ms)</th>
                        <th>دسترسی٪</th>
                        <th>آخرین بررسی</th>
                        <th>۶۰ دقیقه اخیر</th>
                    </tr>
                </thead>
                <tbody id="google-tbody">
                    {% for h in google_hosts %}
                    <tr data-name="{{ h.name }}" data-host="{{ h.host }}">
                        <td><div class="service-name-cell"><span class="status-indicator pending"></span><span class="service-name">{{ h.name }}</span></div></td>
                        <td><span class="host-badge" title="{{ h.host }}">{{ h.host | replace("https://", "") | replace("http://", "") }}</span></td>
                        <td><span class="status-badge">—</span></td>
                        <td><span class="delay">—</span></td>
                        <td class="uptime-cell"><span class="uptime-badge">—</span></td>
                        <td class="time-cell">—</td>
                        <td><div class="sparkline"></div></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <div class="footer">
        ساخته شده با ☕ و ❤️ توسط <a href="https://t.me/rynave" target="_blank">حامد</a>
    </div>
</div>

<script>
    const MAX_HISTORY = {{ max_history }};
    let isUpdating = false;
    const refreshBtn = document.getElementById('manual-refresh');
    const updateTimeSpan = document.getElementById('update-time');

    // ذخیره وضعیت قبلی برای انیمیشن
    const previousStatus = {};

    // نمایش لودینگ اولیه (اسکلتون) - در واقع داده‌ها به سرعت جایگزین می‌شوند
    function showSkeleton() {
        document.querySelectorAll('tbody tr').forEach(row => {
            // می‌توان کلاس اسکلتون اضافه کرد اما چون داده بلافاصله می‌آید نیاز نیست
        });
    }

    // به‌روزرسانی جداول
    function updateTable(tableId, data) {
        const tbody = document.getElementById(tableId + '-tbody') || document.querySelector(`#${tableId} tbody`);
        if (!tbody) return;
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(row => {
            const name = row.getAttribute('data-name');
            const serviceData = data[name];
            if (!serviceData) return;

            const current = serviceData.current;
            const history = serviceData.history || [];

            // انیمیشن تغییر وضعیت
            const currentSuccess = current.success;
            const prev = previousStatus[name];
            if (prev !== undefined && currentSuccess !== null && prev !== currentSuccess) {
                row.classList.add('row-updating');
                setTimeout(() => row.classList.remove('row-updating'), 1000);
            }
            previousStatus[name] = currentSuccess;

            // آپدیت نشانگر وضعیت
            const indicator = row.querySelector('.status-indicator');
            const statusBadge = row.querySelector('.status-badge');
            if (current.success === true) {
                indicator.className = 'status-indicator up';
                statusBadge.className = 'status-badge up';
                statusBadge.innerHTML = `✅ فعال ${current.status_code ? '<span style="margin-right:4px;opacity:0.8">'+current.status_code+'</span>' : ''}`;
            } else if (current.success === false) {
                indicator.className = 'status-indicator down';
                statusBadge.className = 'status-badge down';
                statusBadge.textContent = '❌ قطع';
            } else {
                indicator.className = 'status-indicator pending';
                statusBadge.className = 'status-badge';
                statusBadge.textContent = '—';
            }

            // تاخیر
            const delaySpan = row.querySelector('.delay');
            delaySpan.textContent = current.delay !== null ? current.delay : '—';

            // درصد دسترسی
            const validCount = history.filter(v => v === 1).length;
            const totalValid = history.filter(v => v !== null).length;
            const uptimePercent = totalValid > 0 ? Math.round((validCount / totalValid) * 100) : 0;
            const uptimeSpan = row.querySelector('.uptime-badge');
            uptimeSpan.textContent = uptimePercent + '%';
            // رنگ پس‌زمینه
            if (uptimePercent >= 95) uptimeSpan.style.background = '#d1fae5';
            else if (uptimePercent >= 80) uptimeSpan.style.background = '#fef3c7';
            else uptimeSpan.style.background = '#fee2e2';

            // زمان بررسی
            row.querySelector('.time-cell').textContent = current.time || '—';

            // نمودار اسپارک‌لاین
            const spark = row.querySelector('.sparkline');
            spark.innerHTML = '';
            for (let i = 0; i < history.length; i++) {
                const bar = document.createElement('div');
                bar.className = 'spark-bar';
                if (history[i] === 1) bar.classList.add('up');
                else if (history[i] === 0) bar.classList.add('down');
                spark.appendChild(bar);
            }
            // پر کردن جای خالی
            for (let i = history.length; i < MAX_HISTORY; i++) {
                const bar = document.createElement('div');
                bar.className = 'spark-bar';
                spark.appendChild(bar);
            }
        });
    }

    // محاسبه و نمایش درصد گروه‌ها
    function updateGroupStats() {
        const groups = [
            { tableId: 'internal-table', progressId: 'internal-progress-fill', percentId: 'internal-group-percent', statId: 'internal-uptime-stat' },
            { tableId: 'external-table', progressId: 'external-progress-fill', percentId: 'external-group-percent', statId: 'external-uptime-stat' },
            { tableId: 'google-table', progressId: 'google-progress-fill', percentId: 'google-group-percent', statId: 'google-uptime-stat' }
        ];

        let totalServices = 0;

        groups.forEach(g => {
            const tbody = document.getElementById(g.tableId + '-tbody') || document.querySelector(`#${g.tableId} tbody`);
            if (!tbody) return;
            const rows = tbody.querySelectorAll('tr');
            let sum = 0;
            let count = 0;
            rows.forEach(row => {
                const uptimeSpan = row.querySelector('.uptime-badge');
                if (uptimeSpan) {
                    const val = parseFloat(uptimeSpan.textContent);
                    if (!isNaN(val)) {
                        sum += val;
                        count++;
                    }
                }
            });
            totalServices += count;
            const avg = count > 0 ? Math.round(sum / count) : 0;
            document.getElementById(g.progressId).style.width = avg + '%';
            document.getElementById(g.percentId).textContent = avg + '%';
            const statEl = document.getElementById(g.statId);
            if (statEl) statEl.textContent = avg + '%';

            // رنگ نوار پیشرفت
            const fill = document.getElementById(g.progressId);
            if (avg >= 95) fill.style.background = '#10b981';
            else if (avg >= 80) fill.style.background = '#f59e0b';
            else fill.style.background = '#ef4444';
        });

        document.getElementById('total-services').textContent = totalServices;
    }

    async function fetchStatus(showLoading = true) {
        if (isUpdating) return;
        isUpdating = true;
        refreshBtn.classList.add('loading');

        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            updateTable('internal-table', data);
            updateTable('external-table', data);
            updateTable('google-table', data);
            updateGroupStats();

            const now = new Date();
            updateTimeSpan.textContent = now.toLocaleTimeString('fa-IR');
        } catch(e) {
            console.error('خطا در دریافت داده:', e);
        } finally {
            isUpdating = false;
            refreshBtn.classList.remove('loading');
        }
    }

    // بارگذاری اولیه
    fetchStatus(false);

    // به‌روزرسانی خودکار هر ۶۰ ثانیه
    setInterval(() => fetchStatus(false), 60000);

    // دکمه رفرش دستی
    refreshBtn.addEventListener('click', () => fetchStatus(true));
</script>
</body>
</html>
"""

@app.route('/api/status')
def api_status():
    with data_lock:
        result = {}
        for name, data in status_data.items():
            result[name] = {
                "current": data["current"].copy(),
                "history": data["history"].copy()
            }
    return jsonify(result)

@app.route('/<path:filename>')
def serve_static(filename):
    response = send_from_directory('.', filename)
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        internal_hosts=INTERNAL_HOSTS,
        external_hosts=EXTERNAL_HOSTS,
        google_hosts=GOOGLE_HOSTS,
        max_history=MAX_HISTORY
    )

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)