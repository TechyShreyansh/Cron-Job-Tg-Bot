from flask import Flask, request
import telebot
import os

TOKEN = "7751696764:AAGmO-BuVoXkydbdKQY9BZYHxLyVtGm4JD4"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

WEBHOOK_URL = "https://testbotbydarkboy.onrender.com/"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"I am running here!\n\nBot Token: `{TOKEN}`", parse_mode="Markdown")

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.data.decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running.', 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
