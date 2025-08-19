import asyncio
import json
import os
from telethon import TelegramClient, events, Button
from flask import Flask
from threading import Thread

from autocatch import register_autocatch
from selfi2 import register_extra_cmds   # دستورات جدا (لیست/آیدی/بلاک/تاریخ/تنظیم)

# --- سرور keep_alive برای ریپلیت ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- خواندن API_ID و API_HASH ---
with open("confing.json", "r", encoding="utf-8") as f:
    config = json.load(f)
API_ID = int(config["api_id"])
API_HASH = config["api_hash"]

SESSIONS = [
    "acc", "acc0", "acc7", "acc8", "acc9",
    "acc10", "acc11", "acc12", "acc13", "accyosef"
]

# فایل مشترک برای گروه‌ها (شناسه‌های تلگرام)
GROUPS_FILE = "groups.json"
if os.path.exists(GROUPS_FILE):
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        GLOBAL_GROUPS = json.load(f)
else:
    GLOBAL_GROUPS = []
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(GLOBAL_GROUPS, f)

def save_groups():
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(GLOBAL_GROUPS, f, ensure_ascii=False, indent=2)

async def setup_client(session_name):
    DATA_FILE = f"data_{session_name}.json"
    state = {
        "owner_id": None,
        "echo_users": [],
        "enabled": True,
        "delay": 2.0,
        "stop_emoji": ["⚜", "💮", "⚡", "❓"],  
        "last_user": None,
        "last_group": None,
        "funny_text": "مگه نیما فشاری 😂",
        "status_msg_id": None,
        "auto_groups": [],     
        "copy_groups": [],
        "copy_plus_user": None   # --- کاربر انتخابی برای کپی پلاس
    }

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            state.update(saved)
        except Exception:
            pass

    def save_state():
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    if not state["owner_id"]:
        state["owner_id"] = me.id
        save_state()
        print(f"✅ [{session_name}] Owner set: {me.id}")
    else:
        print(f"✅ [{session_name}] Started")

    def is_owner(e): 
        return e.sender_id == state["owner_id"]

    # ---------- متن منو وضعیت
    def _status_text():
        return (
            f"🤖 وضعیت ربات {session_name}\n"
            f"═════════════════════════\n"
            f"🔹 وضعیت:\n"
            f"   ✅ فعال: {'بله' if state['enabled'] else 'خیر'}\n"
            f"   ⏳ تاخیر: {state['delay']} ثانیه\n"
            f"   🔄 کاربران کپی: {len(state['echo_users'])}\n"
            f"   ⛔ ایموجی قطع‌کننده: {', '.join(state['stop_emoji']) if state['stop_emoji'] else 'هیچ'}\n"
            f"   📌 گروه‌های ثبت‌شده: {len(GLOBAL_GROUPS)}\n"
            f"   🟢 گروه‌های اتوکچ: {len(state['auto_groups'])}\n"
            f"   🟣 گروه‌های کپی+اتوکچ: {len(state['copy_groups'])}\n"
            f"\n"
            f"📖 دستورات موجود:\n"
            f"   👤 مدیریت کاربران:\n"
            f"      • .کپی (ریپلای)\n"
            f"      • .کپی خاموش (ریپلای)\n"
            f"      • .کپی پلاس (ریپلای)\n"
            f"      • .لیست\n"
            f"   ⚙️ مدیریت ربات:\n"
            f"      • .ریست دیتا\n"
            f"      • .عدد (مثل .0.5)\n"
            f"      • .تنظیم [متن]\n"
            f"      • .ست 😀 💮 ⚡️\n"
            f"      • .ست حذف همه\n"
            f"   🛡 مدیریت گروه/کاربر:\n"
            f"      • .ثبت / .حذف\n"
            f"      • .ثبت کپی\n"
            f"      • .بلاک (ریپلای یا آیدی)\n"
            f"      • .آیدی (ریپلای)\n"
            f"   📅 ابزارها:\n"
            f"      • .تاریخ\n"
        )

    async def send_status():
        try:
            text = _status_text()
            if state.get("status_msg_id"):
                msg = await client.get_messages("me", ids=state["status_msg_id"])
                if msg:
                    await msg.edit(text)
                    return
            sent = await client.send_message("me", text)
            state["status_msg_id"] = sent.id
            save_state()
        except Exception as e:
            print(f"⚠️ خطا در ارسال وضعیت: {e}")

    await send_status()

    # ---------- تغییر تاخیر با '.0.5' و ...
    @client.on(events.NewMessage(pattern=r"\.(\d+(?:\.\d+)?)$"))
    async def set_delay(event):
        if not is_owner(event): return
        try:
            delay = float(event.pattern_match.group(1))
        except Exception:
            return
        state["delay"] = delay
        save_state()
        await event.edit(f"⏳ تاخیر روی {delay} ثانیه تنظیم شد.")
        await send_status()

    # ---------- کپی / کپی خاموش
    @client.on(events.NewMessage(pattern=r".کپی$"))
    async def enable_copy(event):
        if not is_owner(event): return
        if not event.is_reply:
            await event.edit("❌ روی پیام ریپلای کن!")
            return
        reply = await event.get_reply_message()
        user = await reply.get_sender()
        if user.id not in state["echo_users"]:
            state["echo_users"].append(user.id)
            state["last_user"] = user.id
            state["last_group"] = event.chat_id
            save_state()
            await event.edit(f"✅ کپی برای {user.first_name} فعال شد.")
        else:
            await event.edit("ℹ️ قبلاً فعال بود.")
        await send_status()

    @client.on(events.NewMessage(pattern=r".کپی خاموش$"))
    async def disable_copy(event):
        if not is_owner(event): return
        if not event.is_reply:
            await event.edit("❌ روی پیام ریپلای کن!")
            return
        reply = await event.get_reply_message()
        user = await reply.get_sender()
        if user.id in state["echo_users"]:
            state["echo_users"].remove(user.id)
            save_state()
            await event.edit(f"⛔ کپی برای {user.first_name} خاموش شد.")
        else:
            await event.edit("ℹ️ این کاربر فعال نبود.")
        await send_status()

    # ---------- کپی پلاس
    @client.on(events.NewMessage(pattern=r".کپی پلاس$"))
    async def copy_plus(event):
        if not is_owner(event): return
        if not event.is_reply:
            await event.edit("❌ روی پیام ریپلای کن!")
            return
        reply = await event.get_reply_message()
        user = await reply.get_sender()
        state["copy_plus_user"] = user.id
        save_state()
        await event.edit(
            f"✨ کپی پلاس فعال شد برای {user.first_name}\n"
            f"هر وقت اتوکچ قطع شد، دوباره براش فعال میشه.",
            buttons=[[Button.inline("❌ حذف کپی پلاس", b"del_copy_plus")]]
        )
        await send_status()

    @client.on(events.CallbackQuery(pattern=b"del_copy_plus"))
    async def del_copy_plus(event):
        if not is_owner(event): return
        state["copy_plus_user"] = None
        save_state()
        await event.edit("❌ کپی پلاس حذف شد.")
        await send_status()

    # ---------- ریست دیتا
    @client.on(events.NewMessage(pattern=r".ریست دیتا$"))
    async def reset_data(event):
        if not is_owner(event): return
        state.clear()
        state.update({
            "owner_id": event.sender_id,
            "echo_users": [],
            "enabled": True,
            "delay": 2.0,
            "stop_emoji": ["⚜", "💮", "⚡", "❓"],
            "last_user": None,
            "last_group": None,
            "funny_text": "مگه نیما فشاری 😂",
            "status_msg_id": state.get("status_msg_id"),
            "auto_groups": [],
            "copy_groups": [],
            "copy_plus_user": None
        })
        save_state()
        await event.edit("♻️ فایل دیتا ریست شد.")
        await send_status()

    # ---------- ثبت / حذف گروه 
    @client.on(events.NewMessage(pattern=r".ثبت(?:\s+کپی)?$"))
    async def register_group(event):
        if not is_owner(event): return
        if not event.is_group:
            await event.edit("❌ فقط در گروه کار می‌کند.")
            return
        gid = event.chat_id
        if gid not in GLOBAL_GROUPS:
            GLOBAL_GROUPS.append(gid)
            save_groups()
        if "کپی" in event.raw_text:
            if gid not in state["copy_groups"]:
                state["copy_groups"].append(gid)
            text = "✅ گروه برای کپی + اتوکچ ثبت شد."
        else:
            if gid not in state["auto_groups"]:
                state["auto_groups"].append(gid)
            text = "✅ گروه برای اتوکچ ثبت شد."
        save_state()
        await event.edit(text)
        await send_status()

    @client.on(events.NewMessage(pattern=r".حذف$"))
    async def unregister_group(event):
        if not is_owner(event): return
        if not event.is_group:
            await event.edit("❌ فقط در گروه کار می‌کند.")
            return
        gid = event.chat_id
        if gid in GLOBAL_GROUPS:
            GLOBAL_GROUPS.remove(gid)
            save_groups()
        if gid in state["auto_groups"]:
            state["auto_groups"].remove(gid)
        if gid in state["copy_groups"]:
            state["copy_groups"].remove(gid)
        save_state()
        await event.edit("⛔ گروه حذف شد.")
        await send_status()

    # ---------- دستور .ست
    @client.on(events.NewMessage(pattern=r".ست حذف همه$"))
    async def clear_stop_emoji(event):
        if not is_owner(event): return
        state["stop_emoji"] = []
        save_state()
        await event.edit("🧹 ایموجی‌های قطع‌کننده حذف شد.")
        await send_status()

    @client.on(events.NewMessage(pattern=r".ست$"))
    async def show_stop_emoji(event):
        if not is_owner(event): return
        cur = ", ".join(state["stop_emoji"]) if state["stop_emoji"] else "هیچ"
        await event.edit(f"⛔ ایموجی‌های فعلی: {cur}\n"
                         f"برای تنظیم چندتا باهم: `.ست 😀 💮 ⚡️`")

    @client.on(events.NewMessage(pattern=r".ست (.+)$"))
    async def set_stop_emoji(event):
        if not is_owner(event): return
        args = event.pattern_match.group(1).strip()
        tokens = [tok for tok in args.split() if tok]
        seen = set()
        emojis = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                emojis.append(t)
        if len(emojis) > 10:
            emojis = emojis[:10]
        state["stop_emoji"] = emojis
        save_state()
        cur = ", ".join(state["stop_emoji"]) if state["stop_emoji"] else "هیچ"
        await event.edit(f"✅ ایموجی‌های قطع‌کننده تنظیم شد: {cur}")
        await send_status()

    # ---------- موتور کپی
    @client.on(events.NewMessage)
    async def echo(event):
        if not state["enabled"]:
            return
        if event.chat_id not in state["copy_groups"]:
            return
        if event.sender_id in state["echo_users"]:
            await asyncio.sleep(state["delay"])
            try:
                if event.media:
                    await client.send_file(event.chat_id, event.media, caption=event.text)
                else:
                    await client.send_message(event.chat_id, event.text)
            except Exception as e:
                print(f"⚠️ خطا در کپی: {e}")

    # ---------- ماژول‌ها
    register_autocatch(client, state, GLOBAL_GROUPS, save_state, send_status)
    register_extra_cmds(client, state, GLOBAL_GROUPS, save_state, send_status)

    return client

async def main():
    clients = await asyncio.gather(*[setup_client(s) for s in SESSIONS])
    print(f"🚀 {len(clients)} کلاینت ران شد.")
    await asyncio.gather(*[c.run_until_disconnected() for c in clients])

if __name__ == "__main__":
    keep_alive()   # 🔥 اضافه شد برای روشن موندن توی Replit
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
