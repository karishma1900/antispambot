import logging
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
from collections import defaultdict, deque
import time

# Track recent joins in each chat: {chat_id: deque of (timestamp, user_id)}
recent_joins = defaultdict(lambda: deque())

# Thresholds
JOIN_THRESHOLD = 2  # Number of users
TIME_WINDOW = 0.5   # Time window in seconds (detect joins within 0.5 seconds)
API_TOKEN = "8344832442:AAFrvRWPeWl8uLiBbIBw___S7345ickuLxM"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot and Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Stats Storage
spam_stats = {
    "total_spam": 0,
    "deleted": 0,
    "per_user": defaultdict(int),
    "join_spam": defaultdict(int),
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
    if message.chat.type != "private":
        await message.reply("Please chat with me in private.")
        return

    await message.reply(
        "👋 Hello! I am your AntiSpam Bot.\n"
        "Send /spamstats to see spam statistics.\n"
        "Send /userstats <user_id> to check spam stats for a user."
    )

@dp.message()
async def handle_message(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
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

@dp.chat_member()
async def handle_new_chat_members(event: ChatMemberUpdated):
    chat_id = event.chat.id

    # Detect actual "join" (not role changes, kicks, etc.)
    if (
        event.old_chat_member.status in {"left", "kicked"}
        and event.new_chat_member.status == "member"
    ):
        now = time.time()  # Current time in seconds (with floating-point precision)
        user_id = event.new_chat_member.user.id

        # Add join to recent queue
        recent_joins[chat_id].append((now, user_id))

        # Remove joins older than the time window (still keeping them for comparison)
        while recent_joins[chat_id] and now - recent_joins[chat_id][0][0] > TIME_WINDOW:
            recent_joins[chat_id].popleft()

        # If there are 2 or more recent joins within the time window, treat it as spam
        if len(recent_joins[chat_id]) >= JOIN_THRESHOLD:
            logger.warning(f"🚨 Join spam detected in chat {chat_id}! Banning recent joiners.")

            for _, uid in recent_joins[chat_id]:
                try:
                    await bot.ban_chat_member(chat_id, uid)
                    logger.info(f"Banned user {uid} for join spam.")
                    spam_stats["join_spam"][chat_id] += 1
                except Exception as e:
                    logger.warning(f"Failed to ban user {uid}: {e}")

            # ⚠️ Notify group
            await bot.send_message(chat_id, "⚠️ Join spam detected. Recent new users have been banned.")

            # Clear queue after action
            recent_joins[chat_id].clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting bot...")
    await dp.start_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
