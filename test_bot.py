import time
import asyncio
from aiogram.types import ChatMemberUpdated, User, ChatMember
from aiogram import Bot
from bot import handle_new_chat_members  # Importing the bot's main functionality

# Bot token for the TestBot (This bot will simulate the joining users)
API_TOKEN = "8104261349:AAFJiEaNsGWeIuM1bGErug-8l_wuViwOFPg"  # Replace with your actual bot token
bot = Bot(token=API_TOKEN)

# Mocking the bot's behavior for testing purposes
class MockBot:
    async def ban_chat_member(self, chat_id, user_id):
        print(f"Banned user: {user_id}")
        
    async def send_message(self, chat_id, text):
        print(f"Message sent to chat {chat_id}: {text}")

# Create a mock bot instance (used for testing)
bot_instance = MockBot()

# Simulate a user joining the group
async def simulate_user_joining(chat_id, user_id):
    now = time.time()
    event = ChatMemberUpdated(
        chat=types.Chat(id=chat_id, type="group"),
        from_user=User(id=user_id, first_name=f"User {user_id}", last_name="Joiner", is_bot=False, username=f"user{user_id}", language_code="en"),
        old_chat_member=ChatMember(status="left"),
        new_chat_member=ChatMember(status="member"),
        date=int(now)
    )
    # Call the bot's join detection functionality
    await handle_new_chat_members(event)

# Test function for join spam with multiple users
async def test_join_spam_detection():
    chat_id = "@helogrouo"  # The actual Telegram group chat username you want to test
    
    # Simulate user 1 joining
    await simulate_user_joining(chat_id, 1)
    
    # Wait a little time for the next join to happen (simulate rapid joins)
    await asyncio.sleep(0.1)  # 0.1 second delay to simulate a fast join
    
    # Simulate user 2 joining (within the 0.5 second window)
    await simulate_user_joining(chat_id, 2)
    
    # Simulate user 3 joining (still within the 0.5 second window)
    await asyncio.sleep(0.1)  # Add some more delay to simulate more joins
    await simulate_user_joining(chat_id, 3)
    
    # Simulate user 4 joining (still within the 0.5 second window)
    await asyncio.sleep(0.1)
    await simulate_user_joining(chat_id, 4)
    
    # After these users join in rapid succession, check if the bot bans them
    print("Testing completed.")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_join_spam_detection())
