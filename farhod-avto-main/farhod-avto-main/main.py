from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.errors import FloodWaitError, MessageIdInvalidError
from datetime import datetime, time as dt_time
import asyncio

# Telegram API ma'lumotlari
api_id = 16072756
api_hash = '5fc7839a0d020c256e5c901cebd21bb7'
phone = 'YOUR_PHONE_NUMBER'  # Masalan: +99890XXXXXXX

client = TelegramClient('session_name', api_id, api_hash)

# Kanal va guruhlar
NAVOIY_CHANNEL = "Navoiy_uy_joy_kv_barcha_elonlar"
ADDITIONAL_GROUPS = [
    "Navoiy_uy_joy_kvartira_bozori",
    "Navoiy_uy_joy_savdosi"
]

# ⏰ Ish vaqti: 03:00 – 19:00 (kompyuteringiz lokal vaqti bo‘yicha)
def is_working_time():
    now = datetime.now().time()
    return dt_time(3, 0) <= now <= dt_time(1, 0)

# Navoiy kanalidan postlarni olish
async def get_navoiy_posts(min_id=0, limit=100000):
    try:
        channel = await client.get_entity(NAVOIY_CHANNEL)
        messages = await client.get_messages(channel, limit=limit, min_id=min_id)

        if not messages:
            print("Yangi postlar yo‘q.")
            return [], 0

        grouped = {}
        for msg in messages:
            key = msg.grouped_id if msg.grouped_id else msg.id
            grouped.setdefault(key, []).append(msg)

        sorted_posts = [grouped[k] for k in sorted(grouped.keys())]
        next_min_id = messages[0].id
        print(f"{len(sorted_posts)} ta post olindi.")
        return sorted_posts, next_min_id
    except Exception as e:
        print(f"Postlarni olishda xato: {e}")
        return [], min_id

# Bitta guruhga bitta post (yoki postlar to‘plamini) yuborish
async def forward_post(group, post_group):
    try:
        msg_ids = [msg.id for msg in post_group]
        if not msg_ids:
            return
        await client.forward_messages(group.id, msg_ids, NAVOIY_CHANNEL)
        print(f"{group.title} guruhiga post yuborildi.")
        await asyncio.sleep(3)
    except MessageIdInvalidError:
        print("Yaroqsiz message ID.")
    except FloodWaitError as e:
        print(f"Flood: {e.seconds} sek kutish.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"{group.title} ga forwardda xato: {e}")

# Admin bo‘lgan guruhlar va qo‘shimcha guruhlarni olish
async def get_admin_groups():
    try:
        dialogs = await client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=200,
            hash=0
        ))
        groups = [c for c in dialogs.chats if hasattr(c, 'admin_rights') and c.admin_rights]
        for username in ADDITIONAL_GROUPS:
            try:
                g = await client.get_entity(username)
                groups.append(g)
                print(f"Guruh qo‘shildi: {g.title}")
            except Exception as e:
                print(f"{username} guruhini olishda xato: {e}")
        return groups
    except Exception as e:
        print(f"Guruhlarni olishda xato: {e}")
        return []

# Asosiy ishlovchi funksiya
async def main():
    await client.start(phone)
    print("✅ Telegramga ulandik.")

    next_min_id = 0
    post_index = 0
    posts, next_min_id = await get_navoiy_posts(min_id=next_min_id)

    while True:
        if not is_working_time():
            print("⏸ Ish vaqti emas. 60 soniya kutilyapti...")
            await asyncio.sleep(60)
            continue

        groups = await get_admin_groups()
        if not groups:
            print("❌ Guruhlar topilmadi. 60 soniya kutilyapti...")
            await asyncio.sleep(60)
            continue

        for group in groups:
            if post_index + 10 > len(posts):
                print("♻️ Postlar tugadi. Yangilari olinmoqda...")
                posts, next_min_id = await get_navoiy_posts(min_id=next_min_id)
                post_index = 0
                if not posts:
                    print("❌ Yangi post yo‘q. 5 daqiqa kutilyapti...")
                    await asyncio.sleep(300)
                    continue

            batch = posts[post_index:post_index + 10]
            for post_group in batch:
                await forward_post(group, post_group)

            print(f"✅ {group.title} guruhiga 10 ta post yuborildi.")
            post_index += 10

        print("⏱ Barcha guruhlarga yuborildi. 15 minut kutilyapti...")
        await asyncio.sleep(900)

# Dastur ishga tushadi
if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
