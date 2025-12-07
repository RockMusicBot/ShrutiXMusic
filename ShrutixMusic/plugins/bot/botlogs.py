import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import  LOGGER_ID
from ShrutixMusic import nand
from ShrutixMusic.utils.database import add_served_chat, delete_served_chat, get_assistant

welcome_photo = "https://files.catbox.moe/ajobub.jpg"

@nand.on_message(filters.new_chat_members, group=-10)
async def join_watcher(_, message):
    try:
        userbot = await get_assistant(message.chat.id)
        chat = message.chat

        for member in message.new_chat_members:
            if member.id == nand.id:
                count = await nand.get_chat_members_count(chat.id)
                username = message.chat.username if message.chat.username else "Private Group"

                invite_link = ""
                try:
                    if not message.chat.username:
                        link = await nand.export_chat_invite_link(message.chat.id)
                        if link:
                            invite_link = f"\nGroup Link: {link}"
                except:
                    pass

                msg = (
                    f"Music Bot Added In A New Group\n\n"
                    f"Chat Name: {message.chat.title}\n"
                    f"Chat ID: {message.chat.id}\n"
                    f"Chat Username: @{username}\n"
                    f"Group Members: {count}\n"
                    f"Added By: {message.from_user.mention}"
                    f"{invite_link}"
                )

                buttons = []
                if message.from_user.id:
                    buttons.append(
                        [InlineKeyboardButton("Added By", url=f"tg://openmessage?user_id={message.from_user.id}")]
                    )

                await nand.send_photo(
                     LOGGER_ID,
                    photo=welcome_photo,
                    caption=msg,
                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                )

                await add_served_chat(message.chat.id)

                if username:
                    try:
                        await userbot.join_chat(f"@{username}")
                    except:
                        pass

    except Exception as e:
        print(f"Error: {e}")


photo = [
    "https://telegra.ph/file/1949480f01355b4e87d26.jpg",
    "https://telegra.ph/file/3ef2cc0ad2bc548bafb30.jpg",
    "https://telegra.ph/file/a7d663cd2de689b811729.jpg",
    "https://telegra.ph/file/6f19dc23847f5b005e922.jpg",
    "https://telegra.ph/file/2973150dd62fd27a3a6ba.jpg",
]


@nand.on_message(filters.left_chat_member, group=-12)
async def on_left_chat_member(_, message: Message):
    try:
        userbot = await get_assistant(message.chat.id)
        left_chat_member = message.left_chat_member

        if left_chat_member and left_chat_member.id == (await nand.get_me()).id:
            removed_by = message.from_user.mention if message.from_user else "Unknown User"

            caption = (
                f"✫ <b><u>#Left_Group</u></b> ✫\n\n"
                f"Chat Title: {message.chat.title}\n\n"
                f"Chat ID: {message.chat.id}\n\n"
                f"Removed By: {removed_by}\n\n"
                f"Bot: @{nand.username}"
            )

            await nand.send_photo( LOGGER_ID, photo=random.choice(photo), caption=caption)

            await delete_served_chat(message.chat.id)
            await userbot.leave_chat(message.chat.id)

    except:
        pass
