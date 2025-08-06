import time
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatMemberUpdated, User, ChatMember
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from bot import handle_new_chat_members  # Importing the bot's main functionality

# Bot token for the TestBot (This bot will simulate the joining users)
API_TOKEN = "8104261349:AAFJiEaNsGWeIuM1bGErug-8l_wuViwOFPg"  # Replace with your actual bot token
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Track the number of join attempts
join_attempts = 0

# State management class
class Form(StatesGroup):
    waiting_for_group_username = State()

# Function to simulate user joining the group
async def simulate_user_joining(chat_id, user_id):
    global join_attempts
    join_attempts += 1
    now = time.time()

    # Creating the join event
    event = ChatMemberUpdated(
        chat=types.Chat(id=chat_id, type="group"),
        from_user=User(id=user_id, first_name=f"User {user_id}", last_name="Joiner", is_bot=False, username=f"user{user_id}", language_code="en"),
        old_chat_member=ChatMember(status="left"),
        new_chat_member=ChatMember(status="member"),
        date=int(now)
    )
    
    # Call the bot's join detection functionality (anti-spam bot)
    await handle_new_chat_members(event)

    print(f"User {user_id} simulated joining the group.")

# Start command handler
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Please enter the group username (e.g., @helogrouo) to start testing:")
    # Setting the state to waiting for group username
    await Form.waiting_for_group_username.set()

# Handler for receiving group username input
@dp.message_handler(state=Form.waiting_for_group_username)
async def receive_group_username(message: types.Message, state: FSMContext):
    group_username = message.text.strip()

    # Notify user that we're starting the join simulation
    await message.reply(f"Starting join test for group {group_username}...")

    # Simulate users joining the group
    # You can simulate a larger number of users for testing
    for user_id in range(1, 6):  # Simulate users 1 to 5
        await simulate_user_joining(group_username, user_id)
        await asyncio.sleep(0.1)  # Wait for 0.1 seconds between joins (simulate rapid joins)

    # After testing, send a message to the user with the test results
    await message.reply(f"Testing completed for group {group_username}.\n"
                         f"Total attempts to join: {join_attempts}.")

    # Reset the state after the test
    await state.finish()

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
