import os
import asyncio
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import InviteHashExpiredError, InviteHashInvalidError, ChannelPrivateError, FloodWaitError

load_dotenv()
BOT_TOKEN = os.environ.get("CHECKER_BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")


user_data = {}
SESSION_NAME = "checker_bot_session"

async def send_links_as_text(context: ContextTypes.DEFAULT_TYPE, user_id: int, header: str, links: list):
    if not links:
        return

    MAX_LENGTH = 4096
    message_chunk = header + "\n" + ("-"*20) + "\n"

    for link in links:
        if len(message_chunk) + len(link) + 1 > MAX_LENGTH:
            await context.bot.send_message(chat_id=user_id, text=message_chunk, disable_web_page_preview=True)
            message_chunk = ""
        
        message_chunk += link + "\n"

    if message_chunk.strip() != (header + "\n" + ("-"*20)):
        await context.bot.send_message(chat_id=user_id, text=message_chunk, disable_web_page_preview=True)

async def check_links_worker(user_id: int, context: ContextTypes.DEFAULT_TYPE, links_to_check: list):
    global user_data
    
    await context.bot.send_message(chat_id=user_id, text="⚙️ Aapke personal account se login kiya ja raha hai...")
    
    async with TelegramClient(SESSION_NAME, int(API_ID), API_HASH) as client:
        await context.bot.send_message(chat_id=user_id, text="✅ Login successful! Links ki checking shuru ho rahi hai.")
        
        valid_links = []
        invalid_links = []
        total_links = len(links_to_check)
        batch_size = 50
        batch_delay_minutes = 5

        for i in range(0, total_links, batch_size):
            current_batch = links_to_check[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            total_batches = (total_links + batch_size - 1) // batch_size
            
            await context.bot.send_message(chat_id=user_id, text=f"🚀 Batch {batch_number}/{total_batches} shuru ho raha hai ({len(current_batch)} links)...")

            for link_index, link in enumerate(current_batch):
                overall_progress = i + link_index + 1
                try:
                    await asyncio.sleep(15)
                    if overall_progress % 10 == 0:
                        await context.bot.send_message(chat_id=user_id, text=f"⏳ Progress: {overall_progress}/{total_links} links check ho gaye hain...")
                    entity = await client.get_entity(link)
                    print(f"VALID: {link}")
                    valid_links.append(link)
                except (InviteHashExpiredError, InviteHashInvalidError, ChannelPrivateError, ValueError) as e:
                    print(f"INVALID: {link} -> {type(e).__name__}")
                    invalid_links.append(link)
                except FloodWaitError as e:
                    print(f"FLOOD WAIT: Waiting for {e.seconds} seconds.")
                    await context.bot.send_message(chat_id=user_id, text=f"🕒 Flood wait error! Telegram ne {e.seconds} seconds intezar karne ko kaha hai.")
                    await asyncio.sleep(e.seconds)
                    invalid_links.append(link)
                except Exception as e:
                    print(f"UNKNOWN ERROR: {link} -> {e}")
                    invalid_links.append(link)
            
            if i + batch_size < total_links:
                await context.bot.send_message(chat_id=user_id, text=f"☕ Batch {batch_number} poora ho gaya hai. Ab {batch_delay_minutes} minute ka break hai.")
                await asyncio.sleep(batch_delay_minutes * 60)

    await context.bot.send_message(chat_id=user_id, text="🎉 Checking poori ho gayi hai! Yeh rahe results:")

    await send_links_as_text(context, user_id, "✅ Valid Links:", valid_links)
    await send_links_as_text(context, user_id, "❌ Invalid/Expired Links:", invalid_links)

    if user_id in user_data:
        del user_data[user_id]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalam-o-Alaikum! Main Link Checker Bot hoon.\n\n"
        "1️⃣ Mjhe links ki ek `.txt` file bhejein.\n"
        "2️⃣ Phir checking shuru karne ke liye /check command istemal karein."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_data
    user_id = update.message.from_user.id
    
    if user_data.get(user_id, {}).get('is_checking', False):
        await update.message.reply_text("❌ Abhi pichli checking chal rahi hai. Uske poora hone ka intezar karein.")
        return
        
    file = await update.message.document.get_file()
    file_content = (await file.download_as_bytearray()).decode('utf-8')
    
    links = [line.strip() for line in file_content.splitlines() if line.strip()]
    
    if links:
        user_data.setdefault(user_id, {'is_checking': False, 'links': []})
        user_data[user_id]['links'] = links
        await update.message.reply_text(f"✅ File aagayi hai. {len(links)} links check karne ke liye tayyar hain. Ab /check command bhejein.")
    else:
        await update.message.reply_text("❌ Is file mein koi links nahin miley.")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_data
    user_id = update.message.from_user.id
    
    user_info = user_data.get(user_id)
    
    if not user_info or not user_info.get('links'):
        await update.message.reply_text("❌ Pehle links ki `.txt` file bhejein.")
        return
        
    if user_info.get('is_checking', False):
        await update.message.reply_text("⏳ Checking pehle se hi chal rahi hai...")
        return
        
    user_data[user_id]['is_checking'] = True
    links_for_worker = user_data[user_id]['links']
    
    await update.message.reply_text("🚀 Kaam shuru ho raha hai! Yeh process background mein chalega.")
    
    asyncio.create_task(check_links_worker(user_id, context, links_for_worker))

if __name__ == '__main__':
    print("Bot start ho raha hai...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('check', check_command))
    app.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    
    print("Bot ab online hai. Press Ctrl+C to stop.")
    app.run_polling()