# Copyright (C) 2021 VeezMusicProject

from asyncio import QueueEmpty

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from callsmusic import callsmusic
from callsmusic.queues import queues
from config import BOT_USERNAME, COMMAND_PREFIXES, que
from cache.admins import admins
from handlers.play import cb_admin_check
from helpers.channelmusic import get_chat_id
from helpers.dbtools import delcmd_is_on, delcmd_off, delcmd_on, handle_user_status
from helpers.decorators import authorized_users_only, errors
from helpers.filters import command, other_filters
from helpers.helper_functions.admin_check import admin_check
from helpers.helper_functions.extract_user import extract_user
from helpers.helper_functions.string_handling import extract_time


@Client.on_message()
async def _(bot: Client, cmd: Message):
    await handle_user_status(bot, cmd)


# Back Button
BACK_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🏡 Gᴏ Bᴀᴄᴋ", callback_data="cbback")]]
)

# @Client.on_message(filters.text & ~filters.private)
# async def delcmd(_, message: Message):
#    if await delcmd_is_on(message.chat.id) and message.text.startswith("/") or message.text.startswith("!") or message.text.startswith("."):
#        await message.delete()
#    await message.continue_propagation()

# remove the ( # ) if you want the auto del cmd feature is on


@Client.on_message(command(["reload", f"reload@{BOT_USERNAME}"]) & other_filters)
async def update_admin(client, message):
    global admins
    new_admins = []
    new_ads = await client.get_chat_members(message.chat.id, filter="administrators")
    for u in new_ads:
        new_admins.append(u.user.id)
    admins[message.chat.id] = new_admins
    await message.reply_text(
        "✅ Bᴏᴛ **reloaded correctly !**\n✅ **Admin list** ʜᴀs ʙᴇᴇɴ **updated !**"
    )


# Control Menu Of Player
@Client.on_message(command(["control", f"control@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def controlset(_, message: Message):
    await message.reply_text(
        "**💡 Oᴘᴇɴᴇᴅ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ᴄᴏɴᴛʀᴏʟ ᴍᴇɴᴜ!**\n\n**💭 ʏᴏᴜ ᴄᴀɴ ᴄᴏɴᴛʀᴏʟ ᴛʜᴇ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ᴊᴜsᴛ ʙʏ ᴘʀᴇssɪɴɢ ᴏɴᴇ ᴏғ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ**",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏸", callback_data="cbpause"),
                    InlineKeyboardButton("▶️", callback_data="cbresume"),
                ],
                [
                    InlineKeyboardButton("⏩", callback_data="cbskip"),
                    InlineKeyboardButton("⏹", callback_data="cbend"),
                ],
                [InlineKeyboardButton("⛔ Aɴᴛɪ-ᴄᴍᴅ", callback_data="cbdelcmds")],
                [InlineKeyboardButton("🛄 Gʀᴏᴜᴘ-ᴛᴏᴏʟs", callback_data="cbgtools")],
                [InlineKeyboardButton("🗑 Cʟᴏsᴇ", callback_data="close")],
            ]
        ),
    )


@Client.on_message(command(["pause", f"pause@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def pause(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if (chat_id not in callsmusic.pytgcalls.active_calls) or (
        callsmusic.pytgcalls.active_calls[chat_id] == "paused"
    ):
        await message.reply_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘʟᴀʏɪɴɢ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.")
    else:
        callsmusic.pytgcalls.pause_stream(chat_id)
        await message.reply_text(
            "⏸ **Tʀᴀᴄᴋ ᴘᴀᴜsᴇᴅ.**\n\n• **Tᴏ ʀᴇsᴜᴍᴇ ᴛʜᴇ ᴘʟᴀʏʙᴀᴄᴋ, ᴜsᴇ ᴛʜᴇ** » `/resume` ᴄᴏᴍᴍᴀɴᴅ."
        )


@Client.on_message(command(["resume", f"resume@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def resume(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if (chat_id not in callsmusic.pytgcalls.active_calls) or (
        callsmusic.pytgcalls.active_calls[chat_id] == "playing"
    ):
        await message.reply_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘᴀᴜsᴇᴅ.")
    else:
        callsmusic.pytgcalls.resume_stream(chat_id)
        await message.reply_text(
            "▶️ **Tʀᴀᴄᴋ ʀᴇsᴜᴍᴇᴅ.**\n\n• **Tᴏ ᴘᴀᴜsᴇ ᴛʜᴇ ᴘʟᴀʏʙᴀᴄᴋ, ᴜsᴇ ᴛʜᴇ** » `/pause` ᴄᴏᴍᴍᴀɴᴅ."
        )


@Client.on_message(command(["end", f"end@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def stop(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if chat_id not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘʟᴀʏɪɴɢ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.")
    else:
        try:
            queues.clear(chat_id)
        except QueueEmpty:
            pass

        callsmusic.pytgcalls.leave_group_call(chat_id)
        await message.reply_text("✅ **music playback has ended**")


@Client.on_message(command(["skip", f"skip@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def skip(_, message: Message):
    global que
    chat_id = get_chat_id(message.chat)
    if chat_id not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘʟᴀʏɪɴɢ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.")
    else:
        queues.task_done(chat_id)

        if queues.is_empty(chat_id):
            callsmusic.pytgcalls.leave_group_call(chat_id)
        else:
            callsmusic.pytgcalls.change_stream(chat_id, queues.get(chat_id)["file"])

    qeue = que.get(chat_id)
    if qeue:
        qeue.pop(0)
    if not qeue:
        return
    await message.reply_text("⏭ **Yᴏᴜ'ᴠᴇ sᴋɪᴘᴘᴇᴅ ᴛᴏ ᴛʜᴇ ɴᴇxᴛ sᴏɴɢ.**")


@Client.on_message(command(["auth", f"auth@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def authenticate(client, message):
    global admins
    if not message.reply_to_message:
        return await message.reply("💡 Rᴇᴘʟʏ ᴛᴏ ᴍᴇssᴀɢs ᴛᴏ ᴀᴜᴛʜᴏʀɪᴢᴇ ᴜsᴇʀ !")
    if message.reply_to_message.from_user.id not in admins[message.chat.id]:
        new_admins = admins[message.chat.id]
        new_admins.append(message.reply_to_message.from_user.id)
        admins[message.chat.id] = new_admins
        await message.reply(
            "🟢 ᴜsᴇ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ.\n\nFʀᴏᴍ ɴᴏᴡ ᴏɴ, ᴛʜᴀᴛ's ᴜsᴇʀ ᴄᴀɴ ᴜsᴇ  ᴛʜᴇ ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs."
        )
    else:
        await message.reply("✅ Usᴇʀ ᴀʟʀᴇᴀᴅʏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ!")


@Client.on_message(command(["deauth", f"deauth@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def deautenticate(client, message):
    global admins
    if not message.reply_to_message:
        return await message.reply("💡 Rᴇᴘʟʏ ᴛᴏ ᴍᴇssᴀɢs ᴛᴏ ᴅᴇᴀᴜᴛʜᴏʀɪᴢᴇ ᴜsᴇʀ !")
    if message.reply_to_message.from_user.id in admins[message.chat.id]:
        new_admins = admins[message.chat.id]
        new_admins.remove(message.reply_to_message.from_user.id)
        admins[message.chat.id] = new_admins
        await message.reply(
            "🔴 Usᴇʀ ᴅᴇᴀᴜᴛʜᴏʀɪᴢᴇᴅ\n\nFʀᴏᴍ ɴᴏᴡ ᴛʜᴀᴛ's ᴜsᴇʀ ᴄᴀɴ'ᴛ ᴜsᴇ ᴛʜs ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs."
        )
    else:
        await message.reply("✅ Usᴇʀ ᴀʟʀᴇᴀᴅʏ ᴅᴇᴀᴜᴛʜᴏʀɪᴢᴇᴅ!")


# this is a Aɴᴛɪ-ᴄᴍᴅ feature
@Client.on_message(command(["delcmd", f"delcmd@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def delcmdc(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text(
            "Rᴇᴀᴅ ᴛʜᴇ /help ᴍᴇssᴀɢᴇ ᴛᴏ ᴋɴᴏᴡ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ"
        )
    status = message.text.split(None, 1)[1].strip()
    status = status.lower()
    chat_id = message.chat.id
    if status == "on":
        if await delcmd_is_on(message.chat.id):
            return await message.reply_text("✅ Aᴄᴛɪᴠᴀᴛᴇᴅ ᴀᴄᴛɪᴠᴀᴛᴇᴅ")
        await delcmd_on(chat_id)
        await message.reply_text("🟢 Aᴄᴛɪᴠᴀᴛᴇᴅ sᴜᴄᴄsssғᴜʟʟʏ")
    elif status == "off":
        await delcmd_off(chat_id)
        await message.reply_text("🔴 Disabled successfully")
    else:
        await message.reply_text(
            "Rᴇᴀᴅ ᴛʜᴇ /help ᴍᴇssᴀɢᴇ ᴛᴏ ᴋɴᴏᴡ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ"
        )


# music player callbacks (control by buttons feature)


@Client.on_callback_query(filters.regex("cbpause"))
@cb_admin_check
async def cbpause(_, query: CallbackQuery):
    get_chat_id(query.message.chat)
    if (query.message.chat.id not in callsmusic.pytgcalls.active_calls) or (
        callsmusic.pytgcalls.active_calls[query.message.chat.id] == "paused"
    ):
        await query.edit_message_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘʟᴀʏɪɴɢ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", reply_markup=BACK_BUTTON)
    else:
        callsmusic.pytgcalls.pause_stream(query.message.chat.id)
        await query.edit_message_text(
            "⏸ Mᴜsɪᴄ ᴘʟᴀʏʙᴀᴄᴋ ʜᴀs ʙᴇᴇɴ ᴘᴀᴜsᴇᴅ", reply_markup=BACK_BUTTON
        )


@Client.on_callback_query(filters.regex("cbresume"))
@cb_admin_check
async def cbresume(_, query: CallbackQuery):
    get_chat_id(query.message.chat)
    if (query.message.chat.id not in callsmusic.pytgcalls.active_calls) or (
        callsmusic.pytgcalls.active_calls[query.message.chat.id] == "resumed"
    ):
        await query.edit_message_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘᴀᴜsᴇᴅ", reply_markup=BACK_BUTTON)
    else:
        callsmusic.pytgcalls.resume_stream(query.message.chat.id)
        await query.edit_message_text(
            "▶️ Mᴜsɪᴄ ᴘʟᴀʏʙᴀᴄᴋ ʜᴀs ʙᴇᴇɴ ʀᴇsᴜᴍᴇᴅ", reply_markup=BACK_BUTTON
        )


@Client.on_callback_query(filters.regex("cbend"))
@cb_admin_check
async def cbend(_, query: CallbackQuery):
    get_chat_id(query.message.chat)
    if query.message.chat.id not in callsmusic.pytgcalls.active_calls:
        await query.edit_message_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘʟᴀʏɪɴɢ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", reply_markup=BACK_BUTTON)
    else:
        try:
            queues.clear(query.message.chat.id)
        except QueueEmpty:
            pass

        callsmusic.pytgcalls.leave_group_call(query.message.chat.id)
        await query.edit_message_text(
            "✅ Tʜᴇ ᴍᴜsɪᴄ ǫᴜᴇᴜᴇ ʜᴀs ʙᴇᴇɴɴ ᴄʟᴇᴀʀᴇᴅ ᴀɴᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ʟᴇғᴛ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ",
            reply_markup=BACK_BUTTON,
        )


@Client.on_callback_query(filters.regex("cbskip"))
@cb_admin_check
async def cbskip(_, query: CallbackQuery):
    global que
    chat_id = get_chat_id(query.message.chat)
    if query.message.chat.id not in callsmusic.pytgcalls.active_calls:
        await query.edit_message_text("❌ Nᴏ ᴍᴜsɪᴄ ɪs ᴘʟᴀʏɪɴɢ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", reply_markup=BACK_BUTTON)
    else:
        queues.task_done(query.message.chat.id)

        if queues.is_empty(query.message.chat.id):
            callsmusic.pytgcalls.leave_group_call(query.message.chat.id)
        else:
            callsmusic.pytgcalls.change_stream(
                query.message.chat.id, queues.get(query.message.chat.id)["file"]
            )

    qeue = que.get(chat_id)
    if qeue:
        qeue.pop(0)
    if not qeue:
        return
    await query.edit_message_text(
        "⏭ **Yᴏᴜ'ᴠᴇ sᴋɪᴘᴘᴇᴅ ᴛᴏ ᴛʜᴇ ɴᴇxᴛ sᴏɴɢ**", reply_markup=BACK_BUTTON
    )


# (C) Veez Music Project

# ban & unban function


@Client.on_message(filters.command("b", COMMAND_PREFIXES))
@authorized_users_only
async def ban_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    user_id, user_first_name = extract_user(message)

    try:
        await message.chat.kick_member(user_id=user_id)
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ Sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴀɴɴᴇᴅ" f"{user_first_name}" " ғᴏʀᴍ ᴛʜɪs ɢʀᴏᴜᴘ !"
            )
        else:
            await message.reply_text(
                "✅ ʙᴀɴɴᴇᴅ "
                f"<a href='tg://user?id={user_id}'>"
                f"{user_first_name}"
                "</a>"
                " ғᴏʀᴍ ᴛʜɪs ɢʀᴏᴜᴘ !"
            )


@Client.on_message(filters.command("tb", COMMAND_PREFIXES))
@authorized_users_only
async def temp_ban_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    if len(message.command) <= 1:
        return

    user_id, user_first_name = extract_user(message)

    until_date_val = extract_time(message.command[1])
    if until_date_val is None:
        await message.reply_text(
            (
                "Tʜᴇ sᴘᴇᴄɪғɪᴇᴅ ᴛɪᴍᴇ ᴛʏᴘᴇ ᴋs ɪɴᴠᴀʟɪᴅ. " " Usᴇ m, h, or d, Fᴏʀᴍᴀᴛᴅ ᴛɪᴍᴇ: {}"
            ).format(message.command[1][-1])
        )
        return

    try:
        await message.chat.kick_member(user_id=user_id, until_date=until_date_val)
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ Tᴇᴍᴘᴏʀᴀʀɪʟʏ Bᴀɴɴᴇᴅ "
                f"{user_first_name}"
                f" for {message.command[1]}!"
            )
        else:
            await message.reply_text(
                "✅ Tᴇᴍᴘᴏʀᴀʀɪʟʏ Bᴀɴɴᴇᴅ "
                f"<a href='tg://user?id={user_id}'>"
                "ғᴏʀᴍ ᴛʜɪs ɢʀᴏᴜᴘ, "
                "</a>"
                f" for {message.command[1]}!"
            )


@Client.on_message(filters.command(["ub", "um"], COMMAND_PREFIXES))
@authorized_users_only
async def un_ban_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    user_id, user_first_name = extract_user(message)

    try:
        await message.chat.unban_member(user_id=user_id)
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ Oᴋ ᴀᴄᴄᴇᴘᴛsᴅ, ᴜsᴇʀ "
                f"{user_first_name} cᴀɴ"
                " Jᴏɪɴ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ᴀɢᴀɪɴ!"
            )
        else:
            await message.reply_text(
                "✅ Oᴋ, Nᴏᴡ "
                f"<a href='tg://user?id={user_id}'>"
                f"{user_first_name}"
                "</a> Is ɴᴏᴛ"
                " Rᴇsᴛʀɪᴄᴛᴇᴅ ᴀɢᴀɪɴ!"
            )


@Client.on_message(filters.command("m", COMMAND_PREFIXES))
async def mute_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    user_id, user_first_name = extract_user(message)

    try:
        await message.chat.restrict_member(
            user_id=user_id, permissions=ChatPermissions()
        )
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ Oᴋᴀʏ,🏻 " f"{user_first_name}" " Sᴜᴄᴄᴇssғᴜʟʟʏ ᴍᴜᴛᴇᴅ !"
            )
        else:
            await message.reply_text(
                "🏻✅ Oᴋᴀʏ, "
                f"<a href='tg://user?id={user_id}'>"
                "now is"
                "</a>"
                " muted !"
            )


@Client.on_message(filters.command("tm", COMMAND_PREFIXES))
async def temp_mute_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    if len(message.command) <= 1:
        return

    user_id, user_first_name = extract_user(message)

    until_date_val = extract_time(message.command[1])
    if until_date_val is None:
        await message.reply_text(
            (
                "Tʜᴇ sᴘᴇᴄɪғɪᴇᴅ ᴛɪᴍᴇ ᴛʏᴘᴇ ᴋs ɪɴᴠᴀʟɪᴅ. " " Usᴇ m, h, or d, Fᴏʀᴍᴀᴛᴅ ᴛɪᴍᴇ: {}"
            ).format(message.command[1][-1])
        )
        return

    try:
        await message.chat.restrict_member(
            user_id=user_id, permissions=ChatPermissions(), until_date=until_date_val
        )
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "Muted for a while! "
                f"{user_first_name}"
                f" muted for {message.command[1]}!"
            )
        else:
            await message.reply_text(
                "Muted for a while! "
                f"<a href='tg://user?id={user_id}'>"
                "is"
                "</a>"
                " now "
                f" muted, for {message.command[1]}!"
            )