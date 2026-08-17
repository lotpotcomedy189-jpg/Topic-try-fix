import os, re, sys, m3u8, json, time, pytz, asyncio, requests, subprocess, urllib, urllib.parse
import tgcrypto, cloudscraper, random, aiohttp, ffmpeg, shutil, zipfile, aiofiles, yt_dlp

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from logs import logging
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid, MessageNotModified, ButtonUrlInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto

import saini as helper
import globals
from utils import progress_bar, sanitize_text
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS, cookies_file_path

# ======================================================================================
# DRM HANDLER - DIRECT TOPIC CREATION (NO PRE-CHECK)
# ======================================================================================

# Safe senders with fallback to user's DM if channel is invalid
async def safe_send_message(bot, chat_id, text, fallback_chat_id=None, thread_id=None, **kwargs):
    if thread_id:
        kwargs['message_thread_id'] = thread_id
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except PeerIdInvalid:
        if fallback_chat_id:
            await bot.send_message(fallback_chat_id, f"⚠️ Invalid channel ID: `{chat_id}`. Files will be sent here instead.\n\n{text}", **kwargs)
            return None
        else:
            raise
    except TypeError:
        kwargs.pop('message_thread_id', None)
        return await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"Error sending message: {e}")
        if fallback_chat_id:
            await bot.send_message(fallback_chat_id, f"⚠️ Error sending to channel: {e}\n\n{text}", **kwargs)
        return None

async def safe_send_document(bot, chat_id, document, fallback_chat_id=None, thread_id=None, **kwargs):
    if thread_id:
        kwargs['message_thread_id'] = thread_id
    try:
        return await bot.send_document(chat_id, document, **kwargs)
    except PeerIdInvalid:
        if fallback_chat_id:
            await bot.send_message(fallback_chat_id, f"⚠️ Invalid channel ID: `{chat_id}`. Document sent here instead.")
            return await bot.send_document(fallback_chat_id, document, **kwargs)
        else:
            raise
    except TypeError:
        kwargs.pop('message_thread_id', None)
        return await bot.send_document(chat_id, document, **kwargs)
    except Exception as e:
        print(f"Error sending document: {e}")
        if fallback_chat_id:
            await bot.send_document(fallback_chat_id, document, **kwargs)
        return None

async def safe_send_video(bot, chat_id, video, fallback_chat_id=None, thread_id=None, **kwargs):
    if thread_id:
        kwargs['message_thread_id'] = thread_id
    try:
        return await bot.send_video(chat_id, video, **kwargs)
    except PeerIdInvalid:
        if fallback_chat_id:
            await bot.send_message(fallback_chat_id, f"⚠️ Invalid channel ID: `{chat_id}`. Video sent here instead.")
            return await bot.send_video(fallback_chat_id, video, **kwargs)
        else:
            raise
    except TypeError:
        kwargs.pop('message_thread_id', None)
        return await bot.send_video(chat_id, video, **kwargs)
    except Exception as e:
        print(f"Error sending video: {e}")
        if fallback_chat_id:
            await bot.send_video(fallback_chat_id, video, **kwargs)
        return None

async def safe_send_photo(bot, chat_id, photo, fallback_chat_id=None, thread_id=None, **kwargs):
    if thread_id:
        kwargs['message_thread_id'] = thread_id
    try:
        return await bot.send_photo(chat_id, photo, **kwargs)
    except PeerIdInvalid:
        if fallback_chat_id:
            await bot.send_message(fallback_chat_id, f"⚠️ Invalid channel ID: `{chat_id}`. Photo sent here instead.")
            return await bot.send_photo(fallback_chat_id, photo, **kwargs)
        else:
            raise
    except TypeError:
        kwargs.pop('message_thread_id', None)
        return await bot.send_photo(chat_id, photo, **kwargs)
    except Exception as e:
        print(f"Error sending photo: {e}")
        if fallback_chat_id:
            await bot.send_photo(fallback_chat_id, photo, **kwargs)
        return None

async def safe_delete(message):
    if message:
        try:
            await message.delete()
        except Exception as e:
            print(f"Error deleting message: {e}")

# Main handler
async def drm_handler(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    caption = globals.caption
    endfilename = globals.endfilename
    thumb = globals.thumb
    CR = globals.CR
    cwtoken = globals.cwtoken
    cptoken = globals.cptoken
    pwtoken = globals.pwtoken
    vidwatermark = globals.vidwatermark
    raw_text2 = globals.raw_text2
    quality = globals.quality
    res = globals.res
    topic = globals.topic
    topicwise = globals.topicwise

    user_id = m.from_user.id
    fallback_chat_id = m.chat.id

    # Initialize variables to None
    editable = None
    input0 = None
    input1 = None
    input7 = None
    prog = None
    prog1 = None

    if m.document and m.document.file_name.endswith('.txt'):
        x = await m.download()
        await bot.send_document(OWNER, x)
        await m.delete(True)
        file_name, ext = os.path.splitext(os.path.basename(x))
        path = f"./downloads/{m.chat.id}"
        with open(x, "r") as f:
            content = f.read()
        lines = content.split("\n")
        os.remove(x)
    elif m.text and "://" in m.text:
        lines = [m.text]
    else:
        return

    if m.document:
        if m.chat.id not in AUTH_USERS:
            print(f"User ID not in AUTH_USERS", m.chat.id)
            await safe_send_message(bot, m.chat.id, f"<blockquote>__**Oopss! You are not a Premium member\nPLEASE /upgrade YOUR PLAN\nSend me your user id for authorization\nYour User id**__ - `{m.chat.id}`</blockquote>\n", fallback_chat_id=fallback_chat_id)
            return

    pdf_count = 0
    img_count = 0
    v2_count = 0
    mpd_count = 0
    m3u8_count = 0
    yt_count = 0
    drm_count = 0
    zip_count = 0
    other_count = 0
    
    links = []
    for i in lines:
        if "://" in i:
            url = i.split("://", 1)[1]
            links.append(i.split("://", 1))
            if ".pdf" in url:
                pdf_count += 1
            elif url.endswith((".png", ".jpeg", ".jpg")):
                img_count += 1
            elif "v2" in url:
                v2_count += 1
            elif "mpd" in url:
                mpd_count += 1
            elif "m3u8" in url:
                m3u8_count += 1
            elif "drm" in url:
                drm_count += 1
            elif "youtu" in url:
                yt_count += 1
            elif "zip" in url:
                zip_count += 1
            else:
                other_count += 1
                    
    if not links:
        await m.reply_text("<b>🔹Invalid Input.</b>")
        return

    if m.document:
        editable = await m.reply_text(sanitize_text(f"**Total 🔗 links found are {len(links)}\n<blockquote>•PDF : {pdf_count}      •V2 : {v2_count}\n•Img : {img_count}      •YT : {yt_count}\n•zip : {zip_count}       •m3u8 : {m3u8_count}\n•drm : {drm_count}      •Other : {other_count}\n•mpd : {mpd_count}</blockquote>\nSend From where you want to download**"))
        try:
            input0 = await bot.listen(editable.chat.id, timeout=20)
            raw_text = input0.text
            await safe_delete(input0)
        except asyncio.TimeoutError:
            raw_text = '1'
        except Exception as e:
            await m.reply_text(f"Error: {e}")
            return
    
        if int(raw_text) > len(links):
            try:
                await editable.edit(sanitize_text(f"🔹**Enter number in range of Index (01-{len(links)})**"))
            except MessageNotModified:
                pass
            processing_request = False
            await m.reply_text("🔹**Processing Cancled......  **")
            return

        try:
            await editable.edit(sanitize_text(f"**Enter Batch Name or send /d**"))
        except MessageNotModified:
            pass
        try:
            input1 = await bot.listen(editable.chat.id, timeout=20)
            raw_text0 = input1.text
            await safe_delete(input1)
        except asyncio.TimeoutError:
            raw_text0 = '/d'
        except Exception as e:
            await m.reply_text(f"Error: {e}")
            return
      
        if raw_text0 == '/d':
            b_name = file_name.replace('_', ' ')
        else:
            b_name = raw_text0

        try:
            await editable.edit(sanitize_text("__**⚠️Provide the Channel ID or send /d__\n\n<blockquote><i>🔹 Make me an admin to upload.\n🔸Send /id in your channel to get the Channel ID.\n\nExample: Channel ID = -100XXXXXXXXXXX</i></blockquote>\n**"))
        except MessageNotModified:
            pass
        try:
            input7 = await bot.listen(editable.chat.id, timeout=20)
            raw_text7 = input7.text
            await safe_delete(input7)
        except asyncio.TimeoutError:
            raw_text7 = '/d'
        except Exception as e:
            await m.reply_text(f"Error: {e}")
            return

        if "/d" in raw_text7:
            channel_id = m.chat.id
        else:
            channel_id = raw_text7
            # Validate channel ID (just to catch obvious errors)
            try:
                chat = await bot.get_chat(channel_id)
            except Exception as e:
                await m.reply_text(f"⚠️ Invalid Channel ID: `{channel_id}`. Error: {e}\n\nFiles will be sent to your DM instead.")
                channel_id = m.chat.id
                raw_text7 = '/d'
        await safe_delete(editable)

    elif m.text:
        if any(ext in links[i][1] for ext in [".pdf", ".jpeg", ".jpg", ".png"] for i in range(len(links))):
            raw_text = '1'
            raw_text7 = '/d'
            channel_id = m.chat.id
            b_name = '**Link Input**'
            await m.delete()
        else:
            editable = await m.reply_text(sanitize_text(f"╭━━━━❰ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ❱━━➣ \n┣━━⪼ send `144`  for 144p\n┣━━⪼ send `240`  for 240p\n┣━━⪼ send `360`  for 360p\n┣━━⪼ send `480`  for 480p\n┣━━⪼ send `720`  for 720p\n┣━━⪼ send `1080` for 1080p\n╰━━⌈⚡[🦋`{CR}`🦋]⚡⌋━━➣ "))
            try:
                input2 = await bot.listen(editable.chat.id, filters=filters.text & filters.user(m.from_user.id))
                raw_text2 = input2.text
                await safe_delete(input2)
            except asyncio.TimeoutError:
                raw_text2 = '480'
            except Exception as e:
                await m.reply_text(f"Error: {e}")
                return
            quality = f"{raw_text2}p"
            await m.delete()
            try:
                if raw_text2 == "144":
                    res = "256x144"
                elif raw_text2 == "240":
                    res = "426x240"
                elif raw_text2 == "360":
                    res = "640x360"
                elif raw_text2 == "480":
                    res = "854x480"
                elif raw_text2 == "720":
                    res = "1280x720"
                elif raw_text2 == "1080":
                    res = "1920x1080" 
                else: 
                    res = "UN"
            except Exception:
                    res = "UN"
            raw_text = '1'
            raw_text7 = '/d'
            channel_id = m.chat.id
            b_name = '**Link Input**'
            path = os.path.join("downloads", "Free Batch")
            await safe_delete(editable)
        
    if thumb.startswith("http://") or thumb.startswith("https://"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb = thumb

    # ==================== TOPIC-WISE LOGIC - DIRECT CREATE (NO PRE-CHECK) ====================
    topic_threads = {}
    current_topic_for_index = {}

    if topicwise and channel_id != m.chat.id:
        await m.reply_text("🔍 Topic-wise mode is ON. Attempting to create topics directly...")
        
        # Group links by topic (यह हमेशा run होगा)
        topic_groups = {}
        for i, (prefix, url) in enumerate(links):
            raw_title = links[i][0]
            t_match = re.search(r"[\(\[]([^\)\]]+)[\)\]]", raw_title)
            if t_match:
                topic_name = t_match.group(1).strip()
            else:
                topic_name = "General"
            topic_groups.setdefault(topic_name, []).append(i)
            current_topic_for_index[i] = topic_name

        # Ab seedha create_forum_topic call karo, bina kisi condition ke
        created_count = 0
        for topic_name, indices in topic_groups.items():
            try:
                created = await bot.create_forum_topic(channel_id, topic_name)
                topic_threads[topic_name] = created.message_thread_id
                created_count += 1
                await m.reply_text(f"✅ Topic created: `{topic_name}` (Thread ID: {created.message_thread_id})")
            except Exception as e:
                error_text = str(e)
                # Agar error aaya, toh exactly batayega ki kya problem hai
                await m.reply_text(sanitize_text(f"⚠️ Failed to create topic `{topic_name}`: {error_text}"))
                topic_threads[topic_name] = None

        if created_count > 0:
            await m.reply_text(f"✅ Successfully created {created_count} topics!")
        else:
            await m.reply_text("❌ Failed to create ANY topics. Please check:\n"
                               "1. Is this a Supergroup? (Basic groups don't support topics)\n"
                               "2. Are Topics enabled in group settings?\n"
                               "3. Is the bot an admin with 'Create Topics' permission?\n"
                               "4. Did you provide the correct Group ID (not Channel ID)?")
            topicwise = False  # अगर कुछ नहीं बना तो topicwise off कर दो
    # ==================== TOPIC-WISE LOGIC END ====================

    # Pin batch message only if starting from first link (raw_text == 1)
    try:
        if m.document and raw_text == "1" and channel_id != m.chat.id:
            batch_message = await safe_send_message(bot, channel_id, sanitize_text(f"<blockquote><b>🎯Target Batch : {b_name}</b></blockquote>"), fallback_chat_id=fallback_chat_id)
            if batch_message and "/d" not in raw_text7:
                await safe_send_message(bot, m.chat.id, sanitize_text(f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩"), fallback_chat_id=fallback_chat_id)
                try:
                    await bot.pin_chat_message(channel_id, batch_message.id)
                    await bot.delete_messages(channel_id, batch_message.id + 1)
                except Exception as e:
                    await m.reply_text(f"⚠️ Could not pin: {e}")
        else:
            if "/d" not in raw_text7:
                await safe_send_message(bot, m.chat.id, sanitize_text(f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩"), fallback_chat_id=fallback_chat_id)
    except Exception as e:
        await m.reply_text(sanitize_text(f"**Fail Reason »**\n<blockquote><i>{e}</i></blockquote>\n\n✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CR}🌟`"))

    failed_count = 0
    count = int(raw_text)    
    arg = int(raw_text)
    try:
        for i in range(arg-1, len(links)):
            if globals.cancel_requested:
                await m.reply_text("🚦**STOPPED**🚦")
                globals.processing_request = False
                globals.cancel_requested = False
                return

            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            link0 = "https://" + Vxy

            current_topic = current_topic_for_index.get(i, "General") if topicwise else None
            thread_id = topic_threads.get(current_topic, None) if topicwise else None

            name1 = links[i][0].replace("(", "[").replace(")", "]").replace("_", "").replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            if m.text:
                if "youtu" in url:
                    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                    response = requests.get(oembed_url)
                    oembed_data = response.json()
                    audio_title = oembed_data.get('title', 'YouTube Video')
                    audio_title = audio_title.replace("_", " ")
                    name = f'{audio_title[:60]}'
                    name1 = f'{audio_title[:60]}'
                    namef = f'{audio_title[:60]}'
                    thumb = oembed_data.get('thumbnail_url', '')
                    if thumb.startswith("http://") or thumb.startswith("https://"):
                        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
                        thumb = "thumb.jpg"
                else:
                    name = f'{name1[:60]}'
                    namef = f'{name1[:60]}'
            else:
                if topic == "/yes":
                    raw_title = links[i][0]
                    t_match = re.search(r"[\(\[]([^\)\]]+)[\)\]]", raw_title)
                    if t_match:
                        t_name = t_match.group(1).strip()
                        v_name = re.sub(r"^[\(\[][^\)\]]+[\)\]]\s*", "", raw_title)
                        v_name = re.sub(r"[\(\[][^\)\]]+[\)\]]", "", v_name)
                        v_name = re.sub(r":.*", "", v_name).strip()
                    else:
                        t_name = "Untitled"
                        v_name = re.sub(r":.*", "", raw_title).strip()
                    
                    if endfilename == "/d":
                        name = f'{str(count).zfill(3)}) {name1[:60]}'
                        namef = f'{v_name}'
                    else:
                        name = f'{str(count).zfill(3)}) {name1[:60]} {endfilename}'
                        namef = f'{v_name} {endfilename}'
                else:
                    if endfilename == "/d":
                        name = f'{str(count).zfill(3)}) {name1[:60]}'
                        namef = f'{name1[:60]}'
                    else:
                        name = f'{str(count).zfill(3)}) {name1[:60]} {endfilename}'
                        namef = f'{name1[:60]} {endfilename}'

            # ---------- URL Processing ----------
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'
         
            elif "https://cpvod.testbook.com/" in url or "classplusapp.com/drm/" in url:
                url = url.replace("https://cpvod.testbook.com/","https://media-cdn.classplusapp.com/drm/")
                try:
                    url = f"https://sainibotsdrm.vercel.app/api?url={url}&token={cptoken}&auth=4443683167"
                    response = requests.get(url)
                    data = response.json()
                    if data.get("keys") and "url" in data:
                        mpd = data.get('url')
                        keys = data.get('keys')
                        url = mpd
                        keys_string = " ".join([f"--key {key}" for key in keys])
                    else:
                        raise Exception(f"{data.get('error', 'Your Classplus token may be expired.')}")
                        mpd = None
                        keys = None
                        url = None
                        keys_string = None
                except Exception as e:
                    await safe_send_message(bot, channel_id, sanitize_text(f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {url}\n\n<blockquote expandable><i><b>Failed Reason to sign url: {str(e)}</b></i></blockquote>'), fallback_chat_id=fallback_chat_id, thread_id=thread_id, disable_web_page_preview=True)
                    count += 1
                    failed_count += 1
                    continue
                    
            elif "tencdn.classplusapp" in url:
                headers = {'host': 'api.classplusapp.com', 'x-access-token': f'{cptoken}', 'accept-language': 'EN', 'api-version': '18', 'app-version': '1.4.73.2', 'build-number': '35', 'connection': 'Keep-Alive', 'content-type': 'application/json', 'device-details': 'Xiaomi_Redmi 7_SDK-32', 'device-id': 'c28d3cb16bbdac01', 'region': 'IN', 'user-agent': 'Mobile-Android', 'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c', 'accept-encoding': 'gzip'}
                params = {"url": f"{url}"}
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']  
           
            elif 'videos.classplusapp' in url:
                url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': f'{cptoken}'}).json()['url']
            
            elif 'media-cdn.classplusapp.com' in url or 'media-cdn-alisg.classplusapp.com' in url or 'media-cdn-a.classplusapp.com' in url: 
                headers = {'host': 'api.classplusapp.com', 'x-access-token': f'{cptoken}', 'accept-language': 'EN', 'api-version': '18', 'app-version': '1.4.73.2', 'build-number': '35', 'connection': 'Keep-Alive', 'content-type': 'application/json', 'device-details': 'Xiaomi_Redmi 7_SDK-32', 'device-id': 'c28d3cb16bbdac01', 'region': 'IN', 'user-agent': 'Mobile-Android', 'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c', 'accept-encoding': 'gzip'}
                params = {"url": f"{url}"}
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url   = response.json()['url']

            if "edge.api.brightcove.com" in url:
                bcov = f'bcov_auth={cwtoken}'
                url = url.split("bcov_auth")[0]+bcov

            elif "childId" in url and "parentId" in url:
                url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={pwtoken}"
                                      
            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]

            if "youtu" in url:
                ytf = f"bv*[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[height<=?{raw_text2}]"
            elif "embed" in url:
                ytf = f"bestvideo[height<={raw_text2}]+bestaudio/best[height<={raw_text2}]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
           
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            elif "webvideos.classplusapp." in url:
               cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            # ---------- Prepare Captions (sanitized) ----------
            if m.text:
                cc = sanitize_text(f'[{name1} [{res}p].mkv]({link0})')
                cc1 = sanitize_text(f'[{name1}.pdf]({link0})')
                cczip = sanitize_text(f'[{name1}.zip]({link0})')
                ccimg = sanitize_text(f'[{name1}.jpg]({link0})')
                ccm = sanitize_text(f'[{name1}.mp3]({link0})')
                cchtml = sanitize_text(f'[{name1}.html]({link0})')
            else:
                if topic == "/yes":
                    if caption == "/cc1":
                        cc = sanitize_text(f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name} [{res}p].mkv`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        cc1 = sanitize_text(f'[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{v_name}.pdf`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        cczip = sanitize_text(f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{v_name}.zip`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        ccimg = sanitize_text(f'[🖼️]Img Id : {str(count).zfill(3)}\n**Img Title :** `{v_name}.jpg`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        cchtml = sanitize_text(f'[🌐]Html Id : {str(count).zfill(3)}\n**Html Title :** `{v_name}.html`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        ccyt = sanitize_text(f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name}.mp4`\n<a href="{url}">__**Click Here to Watch Stream**__</a>\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        ccm = sanitize_text(f'[🎵]Mp3 Id : {str(count).zfill(3)}\n**Audio Title :** `{v_name}.mp3`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                    elif caption == "/cc2":
                        cc = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote><b>⋅ ─  {t_name}  ─ ⋅</b></blockquote>\n\n<b>🎞️ Title :</b> {v_name}\n<b>├── Extention :  {CR} .mkv</b>\n<b>├── Resolution : [{res}]</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟  𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        cc1 = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote><b>⋅ ─  {t_name}  ─ ⋅</b></blockquote>\n\n<b>📁 Title :</b> {v_name}\n<b>├── Extention :  {CR} .pdf</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        cczip = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote><b>⋅ ─  {t_name}  ─ ⋅</b></blockquote>\n\n<b>📒 Title :</b> {v_name}\n<b>├── Extention :  {CR} .zip</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        ccimg = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote><b>⋅ ─  {t_name}  ─ ⋅</b></blockquote>\n\n<b>🖼️ Title :</b> {v_name}\n<b>├── Extention :  {CR} .jpg</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        ccm = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote><b>⋅ ─  {t_name}  ─ ⋅</b></blockquote>\n\n<b>🎵 Title :</b> {v_name}\n<b>├── Extention :  {CR} .mp3</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        cchtml = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote><b>⋅ ─  {t_name}  ─ ⋅</b></blockquote>\n\n<b>🌐 Title :</b> {v_name}\n<b>├── Extention :  {CR} .html</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                    else:
                        cc = sanitize_text(f'<blockquote><b>⋅ ─ {t_name} ─ ⋅</b></blockquote>\n<b>{str(count).zfill(3)}.</b> {v_name} [{res}p] .mkv')
                        cc1 = sanitize_text(f'<blockquote><b>⋅ ─ {t_name} ─ ⋅</b></blockquote>\n<b>{str(count).zfill(3)}.</b> {v_name} .pdf')
                        cczip = sanitize_text(f'<blockquote><b>⋅ ─ {t_name} ─ ⋅</b></blockquote>\n<b>{str(count).zfill(3)}.</b> {v_name} .zip')
                        ccimg = sanitize_text(f'<blockquote><b>⋅ ─ {t_name} ─ ⋅</b></blockquote>\n<b>{str(count).zfill(3)}.</b> {v_name} .jpg')
                        ccm = sanitize_text(f'<blockquote><b>⋅ ─ {t_name} ─ ⋅</b></blockquote>\n<b>{str(count).zfill(3)}.</b> {v_name} .mp3')
                        cchtml = sanitize_text(f'<blockquote><b>⋅ ─ {t_name} ─ ⋅</b></blockquote>\n<b>{str(count).zfill(3)}.</b> {v_name} .html')
                else:
                    if caption == "/cc1":
                        cc = sanitize_text(f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{name1} [{res}p].mkv`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        cc1 = sanitize_text(f'[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{name1}.pdf`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        cczip = sanitize_text(f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{name1}.zip`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        ccimg = sanitize_text(f'[🖼️]Img Id : {str(count).zfill(3)}\n**Img Title :** `{name1}.jpg`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        ccm = sanitize_text(f'[🎵]Audio Id : {str(count).zfill(3)}\n**Audio Title :** `{name1}.mp3`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                        cchtml = sanitize_text(f'[🌐]Html Id : {str(count).zfill(3)}\n**Html Title :** `{name1}.html`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n** 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} \n')
                    elif caption == "/cc2":
                        cc = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🎞️ Title :</b> {name1}\n<b>├── Extention :  {CR} .mkv</b>\n<b>├── Resolution : [{res}]</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        cc1 = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>📁 Title :</b> {name1}\n<b>├── Extention :  {CR} .pdf</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        cczip = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>📒 Title :</b> {name1}\n<b>├── Extention :  {CR} .zip</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        ccimg = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🖼️ Title :</b> {name1}\n<b>├── Extention :  {CR} .jpg</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        ccm = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🎵 Title :</b> {name1}\n<b>├── Extention :  {CR} .mp3</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                        cchtml = sanitize_text(f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🌐 Title :</b> {name1}\n<b>├── Extention :  {CR} .html</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝑒𝒹 𝒷𝓎 ➤ {CR} **")
                    else:
                        cc = sanitize_text(f'<b>{str(count).zfill(3)}.</b> {name1} [{res}p] .mkv')
                        cc1 = sanitize_text(f'<b>{str(count).zfill(3)}.</b> {name1} .pdf')
                        cczip = sanitize_text(f'<b>{str(count).zfill(3)}.</b> {name1} .zip')
                        ccimg = sanitize_text(f'<b>{str(count).zfill(3)}.</b> {name1} .jpg')
                        ccm = sanitize_text(f'<b>{str(count).zfill(3)}.</b> {name1} .mp3')
                        cchtml = sanitize_text(f'<b>{str(count).zfill(3)}.</b> {name1} .html')

            remaining_links = len(links) - count
            progress = (count / len(links)) * 100
            Show = sanitize_text(f"<i><b>Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>")
            Show1 = sanitize_text(f"<blockquote>🚀𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 » {progress:.2f}%</blockquote>\n┃\n" \
                    f"┣🔗𝐈𝐧𝐝𝐞𝐱 » {count}/{len(links)}\n┃\n" \
                    f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧 » {remaining_links}\n" \
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                    f"<blockquote><b>⚡Dᴏᴡɴʟᴏᴀᴅɪɴɢ Sᴛᴀʀᴛᴇᴅ...⏳</b></blockquote>\n┃\n" \
                    f'┣💃𝐂𝐫𝐞𝐝𝐢𝐭 » {CR}\n┃\n' \
                    f"╰━📚𝐁𝐚𝐭𝐜𝐡 » {b_name}\n" \
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                    f"<blockquote>📚𝐓𝐢𝐭𝐥𝐞 » {namef}</blockquote>\n┃\n" \
                    f"┣🍁𝐐𝐮𝐚𝐥𝐢𝐭𝐲 » {quality}\n┃\n" \
                    f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{link0}">**Original Link**</a>\n┃\n' \
                    f'╰━━🖇️𝐔𝐫𝐥 » <a href="{url}">**Api Link**</a>\n' \
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                    f"🛑**Send** /stop **to stop process**\n┃\n" \
                    f"╰━✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CR}")

            # ---------- Download & Send with safe functions ----------
            if "drive" in url:
                try:
                    ka = await helper.download(url, name)
                    await safe_send_document(bot, channel_id, ka, fallback_chat_id=fallback_chat_id, thread_id=thread_id, caption=cc1)
                    count+=1
                    os.remove(ka)
                except FloodWait as e:
                    await m.reply_text(str(e))
                    time.sleep(e.x)
                    continue    
  
            elif "pdf" in url:
                if "cwmediabkt99" in url:
                    max_retries = 15
                    retry_delay = 4
                    success = False
                    failure_msgs = []
                    
                    for attempt in range(max_retries):
                        try:
                            await asyncio.sleep(retry_delay)
                            url = url.replace(" ", "%20")
                            scraper = cloudscraper.create_scraper()
                            response = scraper.get(url)

                            if response.status_code == 200:
                                with open(f'{namef}.pdf', 'wb') as file:
                                    file.write(response.content)
                                await asyncio.sleep(retry_delay)
                                await safe_send_document(bot, channel_id, f'{namef}.pdf', fallback_chat_id=fallback_chat_id, thread_id=thread_id, caption=cc1)
                                count += 1
                                os.remove(f'{namef}.pdf')
                                success = True
                                break
                            else:
                                failure_msg = await m.reply_text(f"Attempt {attempt + 1}/{max_retries} failed: {response.status_code} {response.reason}")
                                failure_msgs.append(failure_msg)
                                
                        except Exception as e:
                            failure_msg = await m.reply_text(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                            failure_msgs.append(failure_msg)
                            await asyncio.sleep(retry_delay)
                            continue 
                    for msg in failure_msgs:
                        await safe_delete(msg)
                        
                else:
                    try:
                        cmd = f'yt-dlp -o "{namef}.pdf" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        await safe_send_document(bot, channel_id, f'{namef}.pdf', fallback_chat_id=fallback_chat_id, thread_id=thread_id, caption=cc1)
                        count += 1
                        os.remove(f'{namef}.pdf')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue    
           
            elif any(ext in url for ext in [".jpg", ".jpeg", ".png"]):
                try:
                    ext = url.split('.')[-1]
                    cmd = f'yt-dlp -o "{namef}.{ext}" "{url}"'
                    download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                    os.system(download_cmd)
                    await safe_send_photo(bot, channel_id, f'{namef}.{ext}', fallback_chat_id=fallback_chat_id, thread_id=thread_id, caption=ccimg)
                    count += 1
                    os.remove(f'{namef}.{ext}')
                except FloodWait as e:
                    await m.reply_text(str(e))
                    time.sleep(e.x)
                    continue    

            elif any(ext in url for ext in [".mp3", ".wav", ".m4a"]):
                try:
                    ext = url.split('.')[-1]
                    cmd = f'yt-dlp -o "{namef}.{ext}" "{url}"'
                    download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                    os.system(download_cmd)
                    await safe_send_document(bot, channel_id, f'{namef}.{ext}', fallback_chat_id=fallback_chat_id, thread_id=thread_id, caption=ccm)
                    count += 1
                    os.remove(f'{namef}.{ext}')
                except FloodWait as e:
                    await m.reply_text(str(e))
                    time.sleep(e.x)
                    continue    
                    
            elif 'encrypted.m' in url:    
                prog = await safe_send_message(bot, channel_id, Show, fallback_chat_id=fallback_chat_id, thread_id=thread_id, disable_web_page_preview=True)
                prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)  
                filename = res_file  
                await safe_delete(prog1)
                await safe_delete(prog)
                await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, thread_id=thread_id)
                count += 1  
                await asyncio.sleep(1)  
                continue  

            elif 'drmcdni' in url or 'drm/wv' in url or 'drm/common' in url:
                prog = await safe_send_message(bot, channel_id, Show, fallback_chat_id=fallback_chat_id, thread_id=thread_id, disable_web_page_preview=True)
                prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                filename = res_file
                await safe_delete(prog1)
                await safe_delete(prog)
                await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, thread_id=thread_id)
                count += 1
                await asyncio.sleep(1)
                continue
     
            else:
                prog = await safe_send_message(bot, channel_id, Show, fallback_chat_id=fallback_chat_id, thread_id=thread_id, disable_web_page_preview=True)
                prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                res_file = await helper.download_video(url, cmd, name)
                filename = res_file
                await safe_delete(prog1)
                await safe_delete(prog)
                await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, thread_id=thread_id)
                count += 1
                time.sleep(1)

    except Exception as e:
        await m.reply_text(e)
        time.sleep(2)

    success_count = len(links) - int(raw_text) - failed_count + 1
    video_count = len(links) - pdf_count - img_count
    if m.document:
        final_text = sanitize_text(f"<blockquote>🔗 Total URLs: {len(links)} \n┠🔴 Total Failed URLs: {failed_count}\n┠🟢 Total Successful URLs: {success_count}\n┃   ┠🎥 Total Video URLs: {video_count}\n┃   ┠📄 Total PDF URLs: {pdf_count}\n┃   ┠📸 Total IMAGE URLs: {img_count}</blockquote>\n")
        await safe_send_message(bot, channel_id, final_text, fallback_chat_id=fallback_chat_id)
        
        final_text2 = sanitize_text(f"⋅ ─ list index ({raw_text}-{len(links)}) out of range ─ ⋅\n<blockquote><b>📚Batch : {b_name}</b></blockquote>\n⋅ ─ DOWNLOADING ✩ COMPLETED ─ ⋅")
        await safe_send_message(bot, channel_id, final_text2, fallback_chat_id=fallback_chat_id)
        
        if "/d" not in raw_text7:
            await safe_send_message(bot, m.chat.id, sanitize_text(f"<blockquote><b>✅ Your Task is completed, please check your Set Channel📱</b></blockquote>"), fallback_chat_id=fallback_chat_id)

# ============================================================================================================
def register_drm_handlers(bot):
    @bot.on_message(filters.private & (filters.document | filters.text))
    async def call_drm_handler(bot: Client, m: Message):
        await drm_handler(bot, m)
