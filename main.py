import logging
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import Message
from collections import defaultdict

API_TOKEN = "8344832442:AAFrvRWPeWl8uLiBbIBw___S7345ickuLxM"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot and Dispatcher (IMPORTANT: pass bot to Dispatcher!)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)  # <-- Fix here!

# Stats Storage
spam_stats = {
    "total_spam": 0,
    "deleted": 0,
    "per_user": defaultdict(int),
}

# Patterns for detecting spam
SPAM_LINK_PATTERN = re.compile(r"(http[s]?://|t\.me/|bit\.ly|\.com|\.ru|\.cn|\.xyz)")
BANNED_WORDS = {"free", "crypto", "porn", "viagra", "nudes", "xxx"}
MAX_EMOJI_COUNT = 10

def is_spam(message: types.Message) -> bool:
    text = message.text or message.caption or ""

    # 1. Detect links
    if SPAM_LINK_PATTERN.search(text):
        return True

    # 2. Detect banned words
    if any(word in text.lower() for word in BANNED_WORDS):
        return True

    # 3. Too many emojis
    emoji_count = sum(1 for c in text if ord(c) > 10000)
    if emoji_count > MAX_EMOJI_COUNT:
        return True

    return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Only respond in private chat
    if message.chat.type != ChatType.PRIVATE:
        await message.reply("Please chat with me in private.")
        return

    await message.reply(
        "👋 Hello! I am your AntiSpam Bot.\n"
        "Send /spamstats to see spam statistics.\n"
        "Send /userstats <user_id> to check spam stats for a user."
    )

@dp.message()
async def handle_message(message: types.Message):
    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return  # Ignore private chats

    if message.from_user.is_bot:
        return  # Ignore other bots

    if is_spam(message):
        try:
            await message.delete()
            spam_stats["total_spam"] += 1
            spam_stats["deleted"] += 1
            spam_stats["per_user"][message.from_user.id] += 1
            logger.info(f"Deleted spam from {message.from_user.full_name}")
        except Exception as e:
            logger.warning(f"Failed to delete message: {e}")

@dp.message(Command("spamstats"))
async def cmd_spamstats(message: types.Message):
    logger.info(f"Received /spamstats from user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type != ChatType.PRIVATE:
        await message.reply("Please chat with me in private to see spam stats.")
        return

    total = spam_stats["total_spam"]
    deleted = spam_stats["deleted"]
    await message.reply(f"🛡️ Spam Stats:\nTotal spam detected: {total}\nMessages deleted: {deleted}")

@dp.message(Command("userstats"))
async def cmd_userstats(message: types.Message):
    # Only allow in private chat
    if message.chat.type != ChatType.PRIVATE:
        await message.reply("Please chat with me in private to check user spam stats.")
        return

    args = message.get_args()
    if not args:
        await message.reply("Please provide a user ID. Usage: /userstats <user_id>")
        return

    try:
        user_id = int(args)
    except ValueError:
        await message.reply("Invalid user ID format. Please provide a numeric user ID.")
        return

    count = spam_stats["per_user"].get(user_id, 0)
    await message.reply(f"👤 Spam stats for user ID {user_id}:\nSpam messages: {count}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
