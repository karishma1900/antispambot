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
kicked_users = defaultdict(int)
# Stats Storage
spam_stats = {
    "total_spam": 0,
    "deleted": 0,
    "per_user": defaultdict(int),
}

# Bulk Join Detection
JOIN_WINDOW = timedelta(seconds=10)  # Time window for bulk join detection

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

# Change recent_joins to store tuples: (timestamp, user_id, chat_id)
recent_joins = []

async def remove_user_if_suspect(member: types.ChatMember):
    if member.user.is_bot:
        return

    # Suspicious username check
    if SPAM_LINK_PATTERN.search(member.user.username or ""):
        try:
            await bot.kick_chat_member(member.chat.id, member.user.id)
            kicked_users[member.user.id] += 1   # <-- Track kicked user
            logger.info(f"Suspicious user {member.user.full_name} removed due to a suspicious link.")
        except Exception as e:
            logger.warning(f"Failed to remove user: {e}")

    now = datetime.now()
    recent_joins.append((now, member.user.id, member.chat.id))

    # Filter recent joins
    recent_joins[:] = [(t, u, c) for (t, u, c) in recent_joins if now - t < JOIN_WINDOW]

    if len(recent_joins) > 3:  # Bulk join detected
        for _, user_id, chat_id in recent_joins:
            try:
                await bot.kick_chat_member(chat_id, user_id)
                kicked_users[user_id] += 1  # <-- Track kicked user here too
                logger.info(f"Bulk join detected, removed user ID: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to remove user {user_id}: {e}")

        recent_joins.clear()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Only respond in private chat
    if message.chat.type != ChatType.PRIVATE:
        await message.reply("Please chat with me in private.")
        return

    await message.reply(
        "👋 Hello! I am your AntiSpam Bot.\n"
        "Send /spamstats to see spam statistics.\n"
        
    )


@dp.message(Command("spamstats"))
async def cmd_spamstats(message: types.Message):
    logger.info(f"Received /spamstats command from {message.from_user.full_name} in chat {message.chat.id}")
    try:
        total = spam_stats["total_spam"]
        deleted = spam_stats["deleted"]

        # Prepare kicked users info
        kicked_user_info = []
        for user_id, kick_count in kicked_users.items():
            try:
                user = await bot.get_chat_member(message.chat.id, user_id)
                user_name = user.user.full_name
                kicked_user_info.append(f"{user_name} (User ID: {user_id}) - Removed {kick_count} times")
            except Exception as e:
                logger.error(f"Failed to fetch user info for kicked user {user_id}: {e}")
                kicked_user_info.append(f"User ID {user_id} - Removed {kick_count} times (info unavailable)")

        # Prepare spam users info
        user_spam_info = []
        for user_id, spam_count in spam_stats["per_user"].items():
            try:
                user = await bot.get_chat_member(message.chat.id, user_id)
                user_name = user.user.full_name
                user_spam_info.append(f"{user_name} (User ID: {user_id}) - {spam_count} spam messages")
            except Exception as e:
                logger.error(f"Failed to fetch user info for {user_id}: {e}")
                user_spam_info.append(f"User ID {user_id} - {spam_count} spam messages (info unavailable)")

        kicked_text = (
            "\n\nUsers who were removed from the group:\n" + "\n".join(kicked_user_info)
            if kicked_user_info else "\n\nNo users have been removed from the group yet."
        )

        await message.reply(
            (
                f"🛡️ Spam Stats requested by {message.from_user.full_name}:\n"
                f"Total spam detected: {total}\n"
                f"Messages deleted: {deleted}\n"
                f"Unique users flagged: {len(spam_stats['per_user'])}\n\n"
                f"Users who shared spam messages:\n"
                + ("\n".join(user_spam_info) if user_spam_info else "No users flagged for spam yet.")
                + kicked_text
            )
        )

    except Exception as e:
        logger.error(f"Error in /spamstats command: {e}")
        await message.reply("⚠️ An error occurred while fetching spam stats. Please try again later.")

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
