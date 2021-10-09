import os
from asyncio.queues import QueueEmpty
from os import path
from typing import Callable

import aiofiles
import aiohttp
import ffmpeg
import requests
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtube_search import YoutubeSearch

import converter
from cache.admins import admins as a
from callsmusic import callsmusic
from callsmusic.callsmusic import client as USER
from callsmusic.queues import queues
from config import (
    ASSISTANT_NAME,
    BOT_NAME,
    BOT_USERNAME,
    DURATION_LIMIT,
    GROUP_SUPPORT,
    THUMB_IMG,
    UPDATES_CHANNEL,
    que,
)
from downloaders import youtube
from helpers.admins import get_administrators
from helpers.channelmusic import get_chat_id
from helpers.decorators import authorized_users_only
from helpers.filters import command, other_filters
from helpers.gets import get_file_name

aiohttpsession = aiohttp.ClientSession()
chat_id = None
useer = "NaN"
DISABLED_GROUPS = []


def cb_admin_check(func: Callable) -> Callable:
    async def decorator(client, cb):
        admemes = a.get(cb.message.chat.id)
        if cb.from_user.id in admemes:
            return await func(client, cb)
        else:
            await cb.answer("💡 Oɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴛᴀᴘ ᴛʜɪs ʙᴜᴛᴛᴏɴ !", show_alert=True)
            return
    return decorator


def transcode(filename):
    ffmpeg.input(filename).output(
        "input.raw", format="s16le", acodec="pcm_s16le", ac=2, ar="48k"
    ).overwrite_output().run()
    os.remove(filename)


# Convert seconds to mm:ss
def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def generate_cover(title, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()
    image1 = Image.open("./background.png")
    image2 = Image.open("etc/foreground.png")
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("etc/font.otf", 60)
    draw.text((40, 550), "Playing here...", (0, 0, 0), font=font)
    draw.text((40, 630), f"{title[:25]}...", (0, 0, 0), font=font)
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")


@Client.on_message(
    command(["playlist", f"playlist@{BOT_USERNAME}"]) & filters.group & ~filters.edited
)
async def playlist(client, message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return
    queue = que.get(message.chat.id)
    if not queue:
        await message.reply_text("❌ **Nᴏ ᴍᴜsɪᴄ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴘʟᴀʏɪɴʜ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ**")
    temp = []
    for t in queue:
        temp.append(t)
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "💡 **Nᴏᴡ ᴘʟᴀʏɪɴɢ** on {}".format(message.chat.title)
    msg += "\n\n• " + now_playing
    msg += "\n• Rᴇǫ ʙʏ " + by
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "**Queued Song**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n• {name}"
            msg += f"\n• Rᴇǫ ʙʏ {usr}\n"
    await message.reply_text(msg)


# ============================= Settings =========================================
def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.pytgcalls.active_calls:
        stats = "⚙ settings for **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "🎚 volume: {}%\n".format(vol)
            stats += "🎵 song played: `{}`\n".format(len(que))
            stats += "💡 Nᴏᴡ ᴘʟᴀʏɪɴɢ: **{}**\n".format(queue[0][0])
            stats += "🎧 Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ » {}".format(queue[0][1].mention)
    else:
        stats = None
    return stats


def r_ply(type_):
    if type_ == "play":
        pass
    else:
        pass
    mar = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏹", "leave"),
                InlineKeyboardButton("⏸", "puse"),
                InlineKeyboardButton("▶️", "resume"),
                InlineKeyboardButton("⏭", "skip"),
            ],
            [
                InlineKeyboardButton("📖 Pʟᴀʏʟɪsᴛ", "playlist"),
            ],
            [InlineKeyboardButton("🗑 Cʟᴏsᴇ", "cls")],
        ]
    )
    return mar


@Client.on_message(
    command(["player", f"player@{BOT_USERNAME}"]) & filters.group & ~filters.edited
)
@authorized_users_only
async def settings(client, message):
    playing = None
    if message.chat.id in callsmusic.pytgcalls.active_calls:
        playing = True
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        if playing:
            await message.reply(stats, reply_markup=r_ply("pause"))

        else:
            await message.reply(stats, reply_markup=r_ply("play"))
    else:
        await message.reply(
            "◽ **Vᴏɪᴄᴇ ᴄʜᴀᴛ ɴᴏᴛ ғᴏᴜɴᴅ**\n\n» Pʟᴇᴀsᴇ ᴛᴜʀɴ ᴏɴ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ғɪʀsᴛ"
        )


@Client.on_message(
    command(["musicplayer", f"musicplayer@{BOT_USERNAME}"])
    & ~filters.edited
    & ~filters.bot
    & ~filters.private
)
@authorized_users_only
async def music_onoff(_, message):
    global DISABLED_GROUPS
    try:
        message.from_user.id
    except:
        return
    if len(message.command) != 2:
        await message.reply_text(
            "**i'm only know** `/musicplayer on` **and** `/musicplayer off`"
        )
        return
    status = message.text.split(None, 1)[1]
    message.chat.id
    if status == "ON" or status == "on" or status == "On":
        lel = await message.reply("`Pʀᴏᴄᴇssɪɴɢ...`")
        if not message.chat.id in DISABLED_GROUPS:
            await lel.edit("**music player already activated.**")
            return
        DISABLED_GROUPS.remove(message.chat.id)
        await lel.edit(
            f"✅ **Mᴜsɪᴄ ᴘʟᴀʏᴇʀ ʜᴀs ʙᴇᴇɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ɪɴ ᴛʜɪs ᴄʜᴀᴛ..**\n\n💬 `{message.chat.id}`"
        )

    elif status == "OFF" or status == "off" or status == "Off":
        lel = await message.reply("`Pʀᴏᴄᴇssɪɴɢ...`")

        if message.chat.id in DISABLED_GROUPS:
            await lel.edit("**music player already deactivated.**")
            return
        DISABLED_GROUPS.append(message.chat.id)
        await lel.edit(
            f"✅ **Mᴜsɪᴄ ᴘʟᴀʏᴇʀ ʜᴀs ʙᴇᴇɴ ᴅᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ ɪɴ ᴛʜɪs ᴄʜᴀᴛ.**\n\n💬 `{message.chat.id}`"
        )
    else:
        await message.reply_text(
            "**i'm only know** `/musicplayer on` **and** `/musicplayer off`"
        )


@Client.on_callback_query(filters.regex(pattern=r"^(playlist)$"))
async def p_cb(b, cb):
    global que
    que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    cb.message.chat
    cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("❌ **Nᴏ ᴍᴜsɪᴄ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴘʟᴀʏɪɴʜ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ**")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "💡 **Nᴏᴡ ᴘʟᴀʏɪɴɢ** on {}".format(cb.message.chat.title)
        msg += "\n\n• " + now_playing
        msg += "\n• Rᴇǫ ʙʏ " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Queued Song**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n• {name}"
                msg += f"\n• Rᴇǫ ʙʏ {usr}\n"
        await cb.message.edit(msg)


@Client.on_callback_query(
    filters.regex(pattern=r"^(play|pause|skip|leave|puse|resume|menu|cls)$")
)
@cb_admin_check
async def m_cb(b, cb):
    global que
    if (
        cb.message.chat.title.startswith("Channel Music: ")
        and chat.title[14:].isnumeric()
    ):
        chet_id = int(chat.title[13:])
    else:
        chet_id = cb.message.chat.id
    qeue = que.get(chet_id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    m_chat = cb.message.chat

    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "pause":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "paused"
        ):
            await cb.answer(
                "ᴀssɪsᴛᴀɴᴛ ɪs ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ !", show_alert=True
            )
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)

            await cb.answer("Mᴜsɪᴄ Pᴀᴜsᴇᴅ!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("play")
            )

    elif type_ == "play":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "playing"
        ):
            await cb.answer(
                "ᴀssɪsᴛᴀɴᴛ ɪs ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ !", show_alert=True
            )
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("Mᴜsɪᴄ Rᴇsᴜᴍᴇᴅ!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("pause")
            )

    elif type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("nothing in streaming !")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Nᴏᴡ ᴘʟᴀʏɪɴɢ** in {}".format(cb.message.chat.title)
        msg += "\n• " + now_playing
        msg += "\n• Rᴇǫ ʙʏ " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Queued Song**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n• {name}"
                msg += f"\n• Rᴇǫ ʙʏ {usr}\n"
        await cb.message.edit(msg)

    elif type_ == "resume":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "playing"
        ):
            await cb.answer(
                "Vᴏɪᴄᴇ ᴄʜᴀᴛ ɪs ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴘʟᴀʏɪɴɢ", show_alert=True
            )
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("Mᴜsɪᴄ Rᴇsᴜᴍᴇᴅ!")

    elif type_ == "puse":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "paused"
        ):
            await cb.answer(
                "Vᴏɪᴄᴇ ᴄʜᴀᴛ ɪs ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴘᴀᴜsᴇᴅ", show_alert=True
            )
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)

            await cb.answer("Mᴜsɪᴄ Pᴀᴜsᴇᴅ!")

    elif type_ == "cls":
        await cb.answer("Cʟᴏsᴇᴅ ᴍᴇɴᴜ")
        await cb.message.delete()

    elif type_ == "menu":
        stats = updated_stats(cb.message.chat, qeue)
        await cb.answer("menu opened")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏹", "leave"),
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip"),
                ],
                [
                    InlineKeyboardButton("📖 Pʟᴀʏʟɪsᴛ", "playlist"),
                ],
                [InlineKeyboardButton("🗑 Cʟᴏsᴇ", "cls")],
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)

    elif type_ == "skip":
        if qeue:
            qeue.pop(0)
        if chet_id not in callsmusic.pytgcalls.active_calls:
            await cb.answer(
                "ᴀssɪsᴛᴀɴᴛ ɪs ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ !", show_alert=True
            )
        else:
            callsmusic.queues.task_done(chet_id)

            if callsmusic.queues.is_empty(chet_id):
                callsmusic.pytgcalls.leave_group_call(chet_id)

                await cb.message.edit("• Nᴏ ᴍᴏʀᴇ ᴘʟᴀʏʟɪsᴛ\n• Lᴇᴀᴠɪɴɢ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ")
            else:
                callsmusic.pytgcalls.change_stream(
                    chet_id, callsmusic.queues.get(chet_id)["file"]
                )
                await cb.answer("Sᴋɪᴘᴘᴇᴅ")
                await cb.message.edit((m_chat, qeue), reply_markup=r_ply(the_data))
                await cb.message.reply_text(
                    f"⫸ Sᴋɪᴘᴘᴇᴅ ᴛʀᴀᴄᴋ\n⫸ Nᴏᴡ ᴘʟᴀʏɪɴɢ : **{qeue[0][0]}**"
                )

    elif type_ == "leave":
        if chet_id in callsmusic.pytgcalls.active_calls:
            try:
                callsmusic.queues.clear(chet_id)
            except QueueEmpty:
                pass

            callsmusic.pytgcalls.leave_group_call(chet_id)
            await cb.message.edit("✅ Mᴜsɪᴄ ᴘʟᴀʏʙᴀᴄᴋ ʜᴀs ᴇɴᴅᴇᴅ")
        else:
            await cb.answer(
                "ᴀssɪsᴛᴀɴᴛ ɪs ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ !", show_alert=True
            )


@Client.on_message(command(["play", f"play@{BOT_USERNAME}"]) & other_filters)
async def play(_, message: Message):
    global que
    global useer
    if message.chat.id in DISABLED_GROUPS:
        return
    lel = await message.reply("📢 **Fɪɴᴅɪɴɢ ᴍᴜsɪᴄ...**")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id
    try:
        user = await USER.get_me()
    except:
        user.first_name = "music assistant"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        f"<b>💡 Pʟᴇᴀsᴇ ᴀᴅᴅ ᴛʜᴇ ᴜsᴇʀʙᴏᴛ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ.</b>",
                    )
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>💡 Tᴏ ᴜsᴇᴇ ᴍᴇ, I ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴡɪᴛʜ ᴛʜᴇ ᴘᴇʀᴍɪssɪᴏɴs:\n\n» ❌ __Delete messages__\n» ❌ __Ban users__\n» ❌ __Add users__\n» ❌ __Manage voice chat__\n\n**Then type /reload</b>",
                    )
                    return
                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id,
                        "🤖: i'm joined to this group for playing music on voice chat",
                    )
                    await lel.edit(
                        f"✅ **userbot successfully joined this group**",
                    )
                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>❗ Fʟᴏᴏᴅ ᴡᴀɪᴛ ᴇʀʀᴏʀ ❗ \n\nassistant ᴄᴀɴ''ᴛ ᴊᴏɪɴ ᴛʜɪs ɢʀᴏᴜᴘ ᴅᴜᴇ ᴛᴏ ᴍᴀʏ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs ғᴏʀ ᴍᴜsɪᴄʙᴏᴛ."
                        f"\n\nᴏʀ ᴀᴅᴅ  @{ASSISTANT_NAME} ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ᴍᴀɴᴜᴀʟʟʏ ᴛʜᴇɴ ᴛʀʏ ᴀɢᴀɪɴ.</b>",
                    )
    try:
        await USER.get_chat(chid)
    except:
        await lel.edit(
            f"» **Usᴇʀʙᴏᴛ ᴡᴀs ʙᴀɴɴᴇᴅ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ !**\n\n**ᴀsᴋ ᴀᴅᴍɪɴ ᴛᴏ ᴜɴʙᴀɴ @{ASSISTANT_NAME} and added again to this group manually."
        )
        return
    text_links = None
    if message.reply_to_message:
        if message.reply_to_message.audio or message.reply_to_message.voice:
            pass
        entities = []
        toxt = message.reply_to_message.text or message.reply_to_message.caption
        if message.reply_to_message.entities:
            entities = message.reply_to_message.entities + entities
        elif message.reply_to_message.caption_entities:
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == "url"]
        text_links = [entity for entity in entities if entity.type == "text_link"]
    else:
        urls = None
    if text_links:
        urls = True
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(
                f"❌ **Mᴜsɪᴄ ᴡɪᴛʜ ᴅᴜʀᴀᴛɪᴏɴ ᴍᴏʀᴇ ᴛʜᴀɴ** `{DURATION_LIMIT}` **Mɪɴᴜᴛᴇs, ᴄᴀɴ'ᴛ ᴘʟᴀʏ !**"
            )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🖱 Mᴇɴᴜ", callback_data="menu"),
                    InlineKeyboardButton("🗑 Cʟᴏsᴇ", callback_data="cls"),
                ],
                [
                    InlineKeyboardButton(
                        "🌻 Cʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}"
                    )
                ],
            ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/cb1ff510f3bde07b034ee.jpg"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        message.from_user.first_name
        await generate_cover(title, thumbnail)
        file_path = await converter.convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit("📢 **Fɪɴᴅɪɴɢ ᴍᴜsɪᴄ...**")
        ydl_opts = {"format": "bestaudio/best"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:60]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb-{title}-veezmusic.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            results[0]["views"]
        except Exception as e:
            await lel.edit(
                "◽ **Cᴏᴜʟᴅɴ'ᴛ ғɪɴᴅ sᴏɴᴅ ʏᴏᴜ ʀᴇǫᴜᴇsᴛᴇᴅ**\n\n» **Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ sᴏɴɢ ɴᴀᴍᴇ ᴏʀ ɪɴᴄʟᴜᴅᴇ ᴛʜᴇ ᴀʀᴛɪsᴛ's ɴᴀᴍᴇ ᴀs ᴡᴇʟʟ.**"
            )
            print(str(e))
            return
        patch - 8
        dlurl = url
        dlurl = dlurl.replace("youtube", "youtubepp")

        dlurl = url
        dlurl = dlurl.replace("youtube", "youtubepp")
        main
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🖱 Mᴇɴᴜ", callback_data="menu"),
                    InlineKeyboardButton("🗑 Cʟᴏsᴇ", callback_data="cls"),
                ],
                [
                    InlineKeyboardButton(
                        "🌻 Cʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}"
                    )
                ],
            ]
        )
        message.from_user.first_name
        await generate_cover(title, thumbnail)
        file_path = await converter.convert(youtube.download(url))
    else:
        query = ""
        for i in message.command[1:]:
            query += " " + str(i)
        print(query)
        ydl_opts = {"format": "bestaudio/best"}

        try:
            results = YoutubeSearch(query, max_results=5).to_dict()
        except:
            await lel.edit(
                "◽ **Sᴏɴɢ ɴᴀᴍᴇ ɴᴏᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ**\n\n» **ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ɴᴀᴍᴇ ᴏғ sᴏɴɢ ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴘʟᴀʏ.**"
            )
        # veez project
        try:
            toxxt = "\n"
            j = 0
            user = user_name
            emojilist = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            while j < 5:
                toxxt += f"{emojilist[j]} [{results[j]['title'][:25]}...](https://youtube.com{results[j]['url_suffix']})\n"
                toxxt += f" ├ 💡 **Duration** - {results[j]['duration']}\n"
                toxxt += f" └ ⚡ __Powered by {BOT_NAME} AI__\n\n"
                j += 1
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "1️⃣", callback_data=f"plll 0|{query}|{user_id}"
                        ),
                        InlineKeyboardButton(
                            "2️⃣", callback_data=f"plll 1|{query}|{user_id}"
                        ),
                        InlineKeyboardButton(
                            "3️⃣", callback_data=f"plll 2|{query}|{user_id}"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "4️⃣", callback_data=f"plll 3|{query}|{user_id}"
                        ),
                        InlineKeyboardButton(
                            "5️⃣", callback_data=f"plll 4|{query}|{user_id}"
                        ),
                    ],
                    [InlineKeyboardButton(text="🗑 Cʟᴏsᴇ", callback_data="cls")],
                ]
            )
            await message.reply_photo(
                photo=f"{THUMB_IMG}", caption=toxxt, reply_markup=keyboard
            )

            await lel.delete()
            # veez project
            return
            # veez project
        except:
            await lel.edit("__no more results to choose, starting to playing...__")

            # print(results)
            try:
                url = f"https://youtube.com{results[0]['url_suffix']}"
                title = results[0]["title"][:60]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb-{title}-veezmusic.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                results[0]["views"]
            except Exception as e:
                await lel.edit(
                    "◽ **Cᴏᴜʟᴅɴ'ᴛ ғɪɴᴅ sᴏɴᴅ ʏᴏᴜ ʀᴇǫᴜᴇsᴛᴇᴅ**\n\n» **Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ sᴏɴɢ ɴᴀᴍᴇ ᴏʀ ɪɴᴄʟᴜᴅᴇ ᴛʜᴇ ᴀʀᴛɪsᴛ's ɴᴀᴍᴇ ᴀs ᴡᴇʟʟ.**"
                )
                print(str(e))
                return
            dlurl = url
            dlurl = dlurl.replace("youtube", "youtubepp")
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🖱 Mᴇɴᴜ", callback_data="menu"),
                        InlineKeyboardButton("🗑 Cʟᴏsᴇ", callback_data="cls"),
                    ],
                    [
                        InlineKeyboardButton(
                            "🌻 Cʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}"
                        )
                    ],
                ]
            )
            message.from_user.first_name
            await generate_cover(title, thumbnail)
            file_path = await converter.convert(youtube.download(url))
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"💡 **Tʀᴀᴄᴋ ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ »** `{position}`\n\n🏷 **Nᴀᴍᴇ »** [{title[:80]}]({url})\n⏱ **Dᴜʀᴀᴛɪᴏɴ »** `{duration}`\n🎧 **Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ »** {message.from_user.mention}",
            reply_markup=keyboard,
        )
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        except:
            await lel.edit(
                "◽ **Vᴏɪᴄᴇ ᴄʜᴀᴛ ɴᴏᴛ ғᴏᴜɴᴅ**\n\n» Pʟᴇᴀsᴇ ᴛᴜʀɴ ᴏɴ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ғɪʀsᴛ"
            )
            return
        await message.reply_photo(
            photo="final.png",
            caption=f"🏷 **Nᴀᴍᴇ »** [{title[:80]}]({url})\n⏱ **Dᴜʀᴀᴛɪᴏɴ »** `{duration}`\n💡 **Sᴛᴀᴛᴜs »** `Playing`\n"
            + f"🎧 **Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ »** {message.from_user.mention}",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()


@Client.on_callback_query(filters.regex(pattern=r"plll"))
async def lol_cb(b, cb):
    global que
    cbd = cb.data.strip()
    chat_id = cb.message.chat.id
    typed_ = cbd.split(None, 1)[1]
    try:
        x, query, useer_id = typed_.split("|")
    except:
        await cb.message.edit(
            "◽ **Cᴏᴜʟᴅɴ'ᴛ ғɪɴᴅ sᴏɴᴅ ʏᴏᴜ ʀᴇǫᴜᴇsᴛᴇᴅ**\n\n» **Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ sᴏɴɢ ɴᴀᴍᴇ ᴏʀ ɪɴᴄʟᴜᴅᴇ ᴛʜᴇ ᴀʀᴛɪsᴛ's ɴᴀᴍᴇ ᴀs ᴡᴇʟʟ.**"
        )
        return
    useer_id = int(useer_id)
    if cb.from_user.id != useer_id:
        await cb.answer("💡 sorry, this is not for you !", show_alert=True)
        return
    # await cb.message.edit("🔁 **Pʀᴏᴄᴇssɪɴɢ=...**")
    x = int(x)
    try:
        cb.message.reply_to_message.from_user.first_name
    except:
        cb.message.from_user.first_name
    results = YoutubeSearch(query, max_results=5).to_dict()
    resultss = results[x]["url_suffix"]
    title = results[x]["title"][:60]
    thumbnail = results[x]["thumbnails"][0]
    duration = results[x]["duration"]
    results[x]["views"]
    url = f"https://www.youtube.com{resultss}"
    try:
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr) - 1, -1, -1):
            dur += int(dur_arr[i]) * secmul
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
            await cb.message.edit(
                f"❌ **Mᴜsɪᴄ ᴡɪᴛʜ ᴅᴜʀᴀᴛɪᴏɴ ᴍᴏʀᴇ ᴛʜᴀɴ** `{DURATION_LIMIT}` **Mɪɴᴜᴛᴇs, ᴄᴀɴ'ᴛ ᴘʟᴀʏ !**"
            )
            return
    except:
        pass
    try:
        thumb_name = f"thumb-{title}-veezmusic.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
    except Exception as e:
        print(e)
        return
    dlurl = url
    dlurl = dlurl.replace("youtube", "youtubepp")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🖱 Mᴇɴᴜ", callback_data="menu"),
                InlineKeyboardButton("🌻 Cʜᴀɴɴᴇᴘ", url=f"https://t.me/{UPDATES_CHANNEL}"),
            ],
            [InlineKeyboardButton("🗑️ Cʟᴏsᴇ", callback_data="cls")],
        ]
    )
    await generate_cover(title, thumbnail)
    file_path = await converter.convert(youtube.download(url))
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await cb.message.delete()
        await b.send_photo(
            chat_id,
            photo="final.png",
            caption=f"💡 **Tʀᴀᴄᴋ ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ »** `{position}`\n\n🏷 **Nᴀᴍᴇ »** [{title[:80]}]({url})\n⏱ **Dᴜʀᴀᴛɪᴏɴ »** `{duration}`\n🎧 **Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ »** {r_by.mention}",
            reply_markup=keyboard,
        )
    else:
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        await cb.message.delete()
        await b.send_photo(
            chat_id,
            photo="final.png",
            caption=f"🏷 **Nᴀᴍᴇ »** [{title[:80]}]({url})\n⏱ **Dᴜʀᴀᴛɪᴏɴ »** `{duration}`\n💡 **Sᴛᴀᴛᴜs »** `Playing`\n"
            + f"🎧 **Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ »** {r_by.mention}",
            reply_markup=keyboard,
        )
    if path.exists("final.png"):
        os.remove("final.png")


@Client.on_message(command(["ytp", f"ytp@{BOT_USERNAME}"]) & other_filters)
async def ytplay(_, message: Message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return
    lel = await message.reply("📢 **Fɪɴᴅɪɴɢ ᴍᴜsɪᴄ...**")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "music assistant"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        f"💡 **Pʟᴇᴀsᴇ ᴀᴅᴅ ᴛʜᴇ ᴜsᴇʀʙᴏᴛ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ**",
                    )
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "💡 **Tᴏ ᴜsᴇ ᴍᴇ, I ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴡɪᴛʜ ᴛʜᴇ ᴘᴇʀᴍɪssɪᴏɴs:\n\n» ❌ __Delete messages__\n» ❌ __Ban users__\n» ❌ __Add users__\n» ❌ __Manage voice chat__\n\n**Then type /reload**",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id,
                        "🤖: I'ᴍ ᴊᴏɪɴᴇᴅ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ғᴏʀ ᴘʟᴀʏɪɴɢ ᴍᴜsɪᴄ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ",
                    )
                    await lel.edit(
                        f"✅ **Usᴇʀʙᴏᴛ sᴜᴄᴄᴇsᴜʟʟʏ ᴊᴏɪɴᴇᴅ ᴛʜɪs ɢʀᴏᴜᴘ.**",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"❗ **Fʟᴏᴏᴅ ᴡᴀɪᴛ ᴇʀʀᴏʀ** ❗ \n\n**{user.first_name} ᴄᴀɴ''ᴛ ᴊᴏɪɴ ᴛʜɪs ɢʀᴏᴜᴘ ᴅᴜᴇ ᴛᴏ ᴍᴀʏ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs ғᴏʀ ᴍᴜsɪᴄʙᴏᴛ.**"
                        f"\n\n**ᴏʀ ᴀᴅᴅ @{ASSISTANT_NAME} ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ᴍᴀɴᴜᴀʟʟʏ ᴛʜᴇɴ ᴛʀʏ ᴀɢᴀɪɴ.**",
                    )
    try:
        await USER.get_chat(chid)
    except:
        await lel.edit(
            f"💡 **Usᴇʀʙᴏᴛ ᴡᴀs ʙᴀɴɴᴇᴅ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ !** \n\n**ᴀsᴋ ᴀᴅᴍɪɴ ᴛᴏ ᴜɴʙᴀɴ @{ASSISTANT_NAME} ᴀɴᴅ ᴀᴅᴅ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ᴀɢᴀɪɴ ᴍᴀɴᴜᴀʟʟʏ.**"
        )
        return

    message.from_user.id
    message.from_user.first_name

    query = ""
    for i in message.command[1:]:
        query += " " + str(i)
    print(query)
    await lel.edit("🔄 **Cᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ ᴠᴄɢ...**")
    ydl_opts = {"format": "bestaudio/best"}
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        url = f"https://youtube.com{results[0]['url_suffix']}"
        # print(results)
        title = results[0]["title"][:60]
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f"thumb-{title}-veezmusic.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
        duration = results[0]["duration"]
        results[0]["url_suffix"]
        results[0]["views"]

    except Exception as e:
        await lel.edit(
            "◽ **Cᴏᴜʟᴅɴ'ᴛ ғɪɴᴅ sᴏɴᴅ ʏᴏᴜ ʀᴇǫᴜᴇsᴛᴇᴅ**\n\n» **Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ sᴏɴɢ ɴᴀᴍᴇ ᴏʀ ɪɴᴄʟᴜᴅᴇ ᴛʜᴇ ᴀʀᴛɪsᴛ's ɴᴀᴍᴇ ᴀs ᴡᴇʟʟ.**"
        )
        print(str(e))
        return
    try:
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr) - 1, -1, -1):
            dur += int(dur_arr[i]) * secmul
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
            await lel.edit(
                f"❌ **Mᴜsɪᴄ ᴡɪᴛʜ ᴅᴜʀᴀᴛɪᴏɴ ᴍᴏʀᴇ ᴛʜᴀɴ** `{DURATION_LIMIT}` **Mɪɴᴜᴛᴇs, ᴄᴀɴ'ᴛ ᴘʟᴀʏ !**"
            )
            return
    except:
        pass
    dlurl = url
    dlurl = dlurl.replace("youtube", "youtubepp")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🖱 Mᴇɴᴜ", callback_data="menu"),
                InlineKeyboardButton("🗑 Cʟᴏsᴇ", callback_data="cls"),
            ],
            [
                InlineKeyboardButton(
                    "🌻 Cʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}"
                ),
                InlineKeyboardButton("✨ Gʀᴏᴜᴘ", url=f"https://t.me/{GROUP_SUPPORT}"),
            ],
        ]
    )
    message.from_user.first_name
    await generate_cover(title, thumbnail)
    file_path = await converter.convert(youtube.download(url))
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"💡 **Tʀᴀᴄᴋ ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ »** `{position}`\n\n🏷 **Nᴀᴍᴇ »** [{title[:80]}]({url})\n⏱ **Dᴜʀᴀᴛɪᴏɴ »** `{duration}`\n🎧 **Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ »** {message.from_user.mention}",
            reply_markup=keyboard,
        )
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        except:
            await lel.edit(
                "◽ **Vᴏɪᴄᴇ ᴄʜᴀᴛ ɴᴏᴛ ғᴏᴜɴᴅ**\n\n» Pʟᴇᴀsᴇ ᴛᴜʀɴ ᴏɴ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ғɪʀsᴛ"
            )
            return
        await message.reply_photo(
            photo="final.png",
            caption=f"🏷 **Nᴀᴍᴇ »** [{title[:80]}]({url})\n⏱ **Dᴜʀᴀᴛɪᴏɴ »** `{duration}`\n💡 **Sᴛᴀᴛᴜs »** `Playing`\n"
            + f"🎧 **Rᴇǫᴜᴇsᴛᴇᴅ ʙʏ »** {message.from_user.mention}",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()
