import telebot
import sqlite3
from TOKEN import TOKEN
from telebot import types
import re
import os

db_path = os.path.join(os.path.dirname(__file__), 'bot_database.db')

connection = sqlite3.connect(db_path, check_same_thread=False)
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS group_punishments (
    group_id INTEGER PRIMARY KEY,
    punishment TEXT
)
''')
connection.commit()

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['settings'])
def handle_settings(message):
    if message.from_user.id in [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]:
        group_id = message.chat.id
        punishment = get_punishment(group_id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🔨", callback_data="ban"),
                   types.InlineKeyboardButton("🤐", callback_data="mute"),
                   types.InlineKeyboardButton("🥾", callback_data="kick"),
                   types.InlineKeyboardButton("📴", callback_data="off"))
        bot.send_message(message.chat.id, f"Status atual: {punishment}\nSelecione a punição:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Você não é um administrador deste grupo.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.from_user.id in [admin.user.id for admin in bot.get_chat_administrators(call.message.chat.id)]:
        punishment = call.data
        group_id = call.message.chat.id
        save_punishment(group_id, punishment)
        apply_punishment(call.message, punishment)
        new_text = f"👑STATUS ATUAL: {punishment}\n👨‍🔧CONFIGURE A PUNIÇÃO:"
        try:
            sent_message = bot.send_message(chat_id=call.message.chat.id, text=new_text, reply_markup=call.message.reply_markup)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except:
            pass
    else:
        bot.answer_callback_query(call.id, "Você não é um administrador deste grupo.")

def save_punishment(group_id, punishment):
    try:
        cursor.execute("INSERT INTO group_punishments (group_id, punishment) VALUES (?, ?) ON CONFLICT(group_id) DO UPDATE SET punishment = ?", (group_id, punishment, punishment))
        connection.commit()
    except Exception as e:
        print("Erro ao salvar punição:", e)
        connection.rollback()

def get_punishment(group_id):
    try:
        cursor.execute("SELECT punishment FROM group_punishments WHERE group_id = ?", (group_id,))
        punishment = cursor.fetchone()
        if punishment:
            return punishment[0]
        else:
            return "off"
    except Exception as e:
        print("Erro ao obter punição:", e)

def apply_punishment(message, punishment):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    if message.from_user.id != bot.get_me().id:  
        if punishment == "ban":
            bot.kick_chat_member(message.chat.id, message.from_user.id)
        elif punishment == "mute":
            bot.restrict_chat_member(message.chat.id, message.from_user.id, types.ChatPermissions())
        elif punishment == "kick":
            bot.kick_chat_member(message.chat.id, message.from_user.id)
        elif punishment == "off":
            pass 

@bot.message_handler(func=lambda message: True)
def anti_spam(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    if not message.from_user.is_bot:
        member = bot.get_chat_member(chat_id, user_id)
        if not member.status in ["creator", "administrator"]:
            if re.search(r'http[s]?://[^\s<>"]+|www\.[^\s<>"]+', text):
                bot.delete_message(chat_id, message.message_id)
                punishment = get_punishment(chat_id)
                apply_punishment(message, punishment)
                bot.send_message(chat_id, f"Usuário {message.from_user.first_name} foi punido por enviar spam!")

if __name__ == '__main__':
    print("Bot Iniciado!")
    bot.polling()
