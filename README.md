# 🌐 Service Monitoring Dashboard

A lightweight and modern web-based service monitoring dashboard built with **Flask**.

This application continuously monitors the availability and response time of multiple web services and displays their status in a clean, responsive dashboard.

---

## ✨ Features

- 🚀 Real-time monitoring of HTTP/HTTPS services
- 📊 Live response time (latency) measurement
- 📈 60-minute uptime history with sparkline charts
- 🇮🇷 Separate monitoring for Iranian services
- 🌍 Separate monitoring for international services
- ⚙️ Dedicated Google services monitoring
- 🔄 Automatic refresh every minute
- 🔁 Manual refresh button
- 📱 Fully responsive UI
- 🎨 Modern dashboard design
- 🧵 Concurrent health checks using ThreadPoolExecutor
- 🔒 Thread-safe shared data management
- ♻️ Automatic retry for temporary network failures

---

## Dashboard Preview

The dashboard displays:

- Current service status
- HTTP status code
- Response time (ms)
- Uptime percentage
- Last check timestamp
- 60-minute availability history
- Overall group health statistics

---

## Technologies

- Python 3
- Flask
- Requests
- ThreadPoolExecutor
- HTML5
- CSS3
- Vanilla JavaScript

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/service-monitor-dashboard.git

cd service-monitor-dashboard
```

Install dependencies:

```bash
pip install flask requests urllib3
```

Run the application:

```bash
python app.py
```

Open your browser:

```
http://127.0.0.1:5000
```

---

## Project Structure

```
.
├── app.py
├── Vazir-Bold-FD.ttf
├── Arcane Nine.otf
└── README.md
```

---

## Monitored Services

### 🇮🇷 Iranian Services

- Aparat
- Digikala
- Divar
- Snapp
- Torob
- Digiato
- NIC.ir

### 🌍 International Services

- Amazon
- GitHub
- GitLab
- Docker Hub
- ChatGPT
- Spotify
- Steam
- PlayStation
- Cloudflare
- DeepSeek
- PyPI
- Let's Encrypt
- WordPress
- Z AI
- and more...

### ⚙️ Google Services

- Google Search
- Gmail
- Google Drive
- Google Maps
- Google Docs
- Google Sheets
- Google Slides
- Google Meet
- Google Play
- Google Translate
- Google Fonts
- Gemini
- Google News
- Google Scholar

---

## Configuration

You can customize these values inside `app.py`:

```python
MAX_HISTORY = 60
HTTP_TIMEOUT = 2
MAX_WORKERS = 10
```

- **MAX_HISTORY** → Number of historical checks to keep
- **HTTP_TIMEOUT** → Request timeout (seconds)
- **MAX_WORKERS** → Number of concurrent monitoring threads

---

## API

### Get current status

```
GET /api/status
```

Returns JSON containing the current status and monitoring history for all configured services.

---

## How It Works

1. A background thread waits until the next full minute.
2. All services are checked concurrently.
3. Response time and availability are recorded.
4. The dashboard automatically refreshes every 60 seconds.
5. Users can manually trigger a refresh at any time.

---

## Screenshots

Add your screenshots here.

```
screenshots/dashboard.png
```

---

## Future Improvements

- Email notifications
- Telegram alerts
- Prometheus metrics
- Docker support
- Dark mode
- Authentication
- Historical database storage
- Export reports
- Service management UI

---

## License

This project is licensed under the MIT License.

---

## Author

Made with ❤️ by **rynave**
