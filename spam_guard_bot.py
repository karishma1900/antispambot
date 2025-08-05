import logging
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import Message
from collections import defaultdict
import os

API_TOKEN = os.getenv("TOKEN")  # Set your bot token via environment variable

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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
    if not await is_admin(message):
        return

    total = spam_stats["total_spam"]
    deleted = spam_stats["deleted"]
    await message.reply(f"🛡️ Spam Stats:\nTotal spam detected: {total}\nMessages deleted: {deleted}")


@dp.message(Command("userstats"))
async def cmd_userstats(message: types.Message):
    if not await is_admin(message):
        return

    if not message.reply_to_message:
        await message.reply("Please reply to the user's message to check their stats.")
        return

    user = message.reply_to_message.from_user
    count = spam_stats["per_user"].get(user.id, 0)
    await message.reply(f"👤 Spam stats for {user.full_name}:\nSpam messages: {count}")


async def is_admin(message: Message) -> bool:
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in {"administrator", "creator"}
    except:
        return False


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
