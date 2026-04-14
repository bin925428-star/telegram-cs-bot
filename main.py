import telebot
from telebot.types import Message
from flask import Flask
from threading import Thread
import time
import os

# ========== 机器人配置（从环境变量读取，安全） ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7784613616"))

# 初始化机器人
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# 全局变量
forward_map = {}
processed_ids = set()
banned_users = set()
all_users = set()

# ========== Flask 保活服务（Render必须） ==========
app = Flask('TelegramBot')

@app.route('/')
def keep_alive():
    return f"🤖 客服机器人运行中 | 管理员ID: {ADMIN_ID} | 在线用户: {len(all_users)}"

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

# ========== 机器人核心功能（完全保留你原来的逻辑，修复所有语法/缩进） ==========
@bot.message_handler(commands=['start'])
def start(msg: Message):
    all_users.add(msg.from_user.id)
    bot.send_message(msg.chat.id, "✅ 您好！我是客服机器人，有问题请留言，我们会尽快回复您~")

@bot.message_handler(commands=['ban'])
def ban_user(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    if not msg.reply_to_message:
        bot.send_message(ADMIN_ID, "⚠️ 请回复一条用户消息后发送 /ban")
        return
    replied_id = msg.reply_to_message.message_id
    if replied_id not in forward_map:
        bot.send_message(ADMIN_ID, "⚠️ 无法识别该用户，请回复转发过来的用户消息")
        return
    user_id = forward_map[replied_id]
    banned_users.add(user_id)
    bot.send_message(ADMIN_ID, f"🚫 用户 {user_id} 已被拉黑，消息将不再转发")

@bot.message_handler(commands=['unban'])
def unban_user(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    if not msg.reply_to_message:
        bot.send_message(ADMIN_ID, "⚠️ 请回复一条用户消息后发送 /unban")
        return
    replied_id = msg.reply_to_message.message_id
    if replied_id not in forward_map:
        bot.send_message(ADMIN_ID, "⚠️ 无法识别该用户，请回复转发过来的用户消息")
        return
    user_id = forward_map[replied_id]
    if user_id in banned_users:
        banned_users.discard(user_id)
        bot.send_message(ADMIN_ID, f"✅ 用户 {user_id} 已解除拉黑")
    else:
        bot.send_message(ADMIN_ID, f"ℹ️ 用户 {user_id} 不在黑名单中")

@bot.message_handler(commands=['all'])
def broadcast(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    text = msg.text.partition(' ')[2].strip()
    if not text:
        bot.send_message(ADMIN_ID, "⚠️ 请在 /all 后面加上要发送的内容，例如：/all 我爱你")
        return
    if not all_users:
        bot.send_message(ADMIN_ID, "⚠️ 暂无用户记录，无法群发")
        return
    success = 0
    failed = 0
    for uid in all_users:
        try:
            bot.send_message(uid, text)
            success += 1
        except Exception as e:
            failed += 1
    bot.send_message(ADMIN_ID, f"📢 群发完成：成功 {success} 人，失败 {failed} 人")

@bot.message_handler(func=lambda msg: True, content_types=[
    'text', 'photo', 'video', 'document', 'sticker',
    'voice', 'video_note', 'audio', 'animation',
    'contact', 'location'
])
def handle_all(msg: Message):
    if msg.message_id in processed_ids:
        return
    processed_ids.add(msg.message_id)

    if msg.from_user.id == ADMIN_ID:
        if not msg.reply_to_message:
            return
        replied_id = msg.reply_to_message.message_id
        if replied_id not in forward_map:
            return
        user_id = forward_map[replied_id]
        try:
            if msg.text:
                bot.send_message(user_id, msg.text)
            elif msg.photo:
                bot.send_photo(user_id, msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video:
                bot.send_video(user_id, msg.video.file_id, caption=msg.caption)
            elif msg.document:
                bot.send_document(user_id, msg.document.file_id, caption=msg.caption)
            elif msg.sticker:
                bot.send_sticker(user_id, msg.sticker.file_id)
            elif msg.voice:
                bot.send_voice(user_id, msg.voice.file_id, caption=msg.caption)
            elif msg.video_note:
                bot.send_video_note(user_id, msg.video_note.file_id)
            elif msg.audio:
                bot.send_audio(user_id, msg.audio.file_id, caption=msg.caption)
            elif msg.animation:
                bot.send_animation(user_id, msg.animation.file_id, caption=msg.caption)
            bot.send_message(ADMIN_ID, "✅ 回复已发送给用户")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ 发送失败：{str(e)}")
        return

    all_users.add(msg.from_user.id)

    if msg.from_user.id in banned_users:
        return

    try:
        forward_msg = bot.forward_message(ADMIN_ID, msg.chat.id, msg.message_id)
        forward_map[forward_msg.message_id] = msg.from_user.id
    except Exception as e:
        print(f"转发失败：{str(e)}")

# ========== 启动入口（异常自动重启，稳定运行） ==========
def start_bot():
    print("✅ 机器人启动成功，等待消息...")
    while True:
        try:
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=20,
                skip_pending=True,
                none_stop=True,
                interval=1
            )
        except Exception as e:
            print(f"⚠️ 机器人异常重启: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    # 启动Flask保活服务（后台运行）
    Thread(target=run_web_server, daemon=True).start()
    # 启动机器人
    start_bot()
