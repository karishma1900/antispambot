import logging
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import Message
from collections import defaultdict
from datetime import datetime, timedelta

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

# Bulk Join Detection
JOIN_WINDOW = timedelta(seconds=10)  # Time window for bulk join detection
recent_joins = []

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

async def remove_user_if_suspect(member: types.ChatMember):
    """
    Removes a user if they join via a suspicious method.
    This includes joining in bulk or through links that may be malicious.
    """
    if member.user.is_bot:
        return  # Ignore bots

    # Check if the user joined via suspicious link
    if SPAM_LINK_PATTERN.search(member.user.username or ""):
        try:
            await bot.kick_chat_member(member.chat.id, member.user.id)
            logger.info(f"Suspicious user {member.user.full_name} removed due to a suspicious link.")
        except Exception as e:
            logger.warning(f"Failed to remove user: {e}")

    # Check for bulk join (multiple joins within a short time window)
    now = datetime.now()
    recent_joins.append(now)

    # Clean up recent_joins to only keep joins within the valid time window
    recent_joins[:] = [timestamp for timestamp in recent_joins if now - timestamp < JOIN_WINDOW]

    if len(recent_joins) > 3:  # More than 3 joins in 10 seconds -> bulk join suspicion
        try:
            await bot.kick_chat_member(member.chat.id, member.user.id)
            logger.info(f"Bulk join detected, removed user: {member.user.full_name}")
        except Exception as e:
            logger.warning(f"Failed to remove user: {e}")

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
    logger.info(f"Received /spamstats command from user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type != ChatType.PRIVATE:
        logger.info("User is not in a private chat, replying to let them know.")
        await message.reply("Please chat with me in private to see spam stats.")
        return

    total = spam_stats["total_spam"]
    deleted = spam_stats["deleted"]
    logger.info(f"Spam stats: Total detected spam: {total}, Total deleted: {deleted}")
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

@dp.chat_member()
async def on_user_join(member: types.ChatMemberUpdated):
    # Check if the new member joined the group
    if member.new_chat_member.status == "member":
        await remove_user_if_suspect(member.new_chat_member)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
