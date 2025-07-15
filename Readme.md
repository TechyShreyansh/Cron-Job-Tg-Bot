# ✅ Cron-Job Telegram Bot

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)  
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)  
[![Deploy on Koyeb](https://img.shields.io/badge/Deploy-Koyeb-orange)](https://www.koyeb.com/)  

A **lightweight Telegram Bot** that allows you to **create, manage, and automate cron jobs directly from Telegram**.  
Perfect for running scheduled tasks, reminders, or any automation with an intuitive chat interface.  

---

## ✨ Features  

✅ **Create & Manage Cron Jobs** via Telegram  
✅ **Simple and Minimal** – no complex setup required  
✅ **Secure** – Only authorized users can manage jobs  
✅ **Cross-platform Hosting** (Koyeb, VPS, Heroku, etc.)  
✅ **Python-based** with easy deployment  

---

## 📂 Project Structure  

```
Cron-Job-Tg-Bot/
 ├── main.py          # Main bot script  
 ├── app.py           # Alternate entrypoint  
 ├── app2.py          # Another variant (optional)
 ├── requirements.txt # Python dependencies  
 └── Readme.md        # Basic info (this will replace it)
```

---

## 🛠️ Requirements  

- Python **3.9+**  
- A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)  
- (Optional) **Koyeb / VPS / Heroku** account for hosting  

---

## 🚀 Installation  

### 1️⃣ Clone the Repository  

```bash
git clone https://github.com/your-username/Cron-Job-Tg-Bot.git
cd Cron-Job-Tg-Bot
```

### 2️⃣ Install Dependencies  

```bash
pip install -r requirements.txt
```

### 3️⃣ Set Environment Variables  

Create a `.env` file or export variables in your shell:  

```bash
export BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
export AUTH_USER_ID=YOUR_TELEGRAM_USER_ID   # only you can manage jobs
```

### 4️⃣ Run Locally  

```bash
python3 main.py
```

Your bot will now run locally! 🎉  

---

## 🌐 Deployment  

You can deploy on **Koyeb**, **Heroku**, or any **Linux VPS**.  

---
