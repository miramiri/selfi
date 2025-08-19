# -*- coding: utf-8 -*-
# selfi2_fixed.py

from datetime import datetime

import jdatetime
import pytz
from telethon import events
from telethon.tl.functions.contacts import BlockRequest
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji


def register_extra_cmds(client, state, GLOBAL_GROUPS, save_state, send_status):
    def is_owner(e):
        return e.sender_id == state["owner_id"]

    # --- لیست کاربران و گروه‌ها (نمایش echo_users و copy_plus برگردانده شد)
    @client.on(events.NewMessage(pattern=r"^.لیست$"))
    async def list_items(event):
        if not is_owner(event):
            return

        text = "🔄 وضعیت کاربران و گروه‌ها:\n\n"

        # کاربران کپی
        echo_users = state.get("echo_users", [])
        if echo_users:
            lines = []
            for uid in echo_users:
                try:
                    u = await client.get_entity(uid)
                    fname = getattr(u, "first_name", "") or ""
                    lines.append(f"👤 {fname} — `{uid}`")
                except Exception:
                    lines.append(f"👤 `{uid}`")
            text += "👥 کاربران کپی:\n" + "\n".join(lines) + "\n\n"
        else:
            text += "👥 کاربران کپی: (هیچ)\n\n"

        # کاربران کپی پلاس
        copy_plus = state.get("copy_plus", [])
        if copy_plus:
            lines = []
            for uid in copy_plus:
                try:
                    u = await client.get_entity(uid)
                    fname = getattr(u, "first_name", "") or ""
                    lines.append(f"⭐ {fname} — `{uid}`")
                except Exception:
                    lines.append(f"⭐ `{uid}`")
            text += "✨ کاربران کپی پلاس:\n" + "\n".join(lines) + "\n\n"
        else:
            text += "✨ کاربران کپی پلاس: (هیچ)\n\n"

        # گروه‌های عادی (فقط اتوکچ)
        auto_groups = state.get("auto_groups", [])
        if auto_groups:
            lines = []
            for gid in auto_groups:
                try:
                    g = await client.get_entity(gid)
                    title = getattr(g, "title", "گروه")
                    lines.append(f"🟢 {title} — `{gid}`")
                except Exception:
                    lines.append(f"🟢 `{gid}`")
            text += "🏷 گروه‌های اتوکچ:\n" + "\n".join(lines) + "\n\n"
        else:
            text += "🏷 گروه‌های اتوکچ: (هیچ)\n\n"

        # گروه‌های کپی + اتوکچ
        copy_groups = state.get("copy_groups", [])
        if copy_groups:
            lines = []
            for gid in copy_groups:
                try:
                    g = await client.get_entity(gid)
                    title = getattr(g, "title", "گروه")
                    lines.append(f"🟣 {title} — `{gid}`")
                except Exception:
                    lines.append(f"🟣 `{gid}`")
            text += "🏷 گروه‌های کپی+اتوکچ:\n" + "\n".join(lines)
        else:
            text += "🏷 گروه‌های کپی+اتوکچ: (هیچ)"

        await event.edit(text)

    # --- تنظیم متن طنز
    @client.on(events.NewMessage(pattern=r"^.تنظیم (.+)$"))
    async def set_funny_text(event):
        if not is_owner(event):
            return
        txt = event.pattern_match.group(1).strip()
        state["funny_text"] = txt
        save_state()
        await event.edit(f"✅ متن تنظیم شد: {txt}")
        await send_status()

    # --- بلاک کاربر
    @client.on(events.NewMessage(pattern=r"^.بلاک(?:\s+(\d+))?$"))
    async def block_user(event):
        if not is_owner(event):
            return

        uid = None
        if event.pattern_match.group(1):
            uid = int(event.pattern_match.group(1))
        elif event.is_reply:
            reply = await event.get_reply_message()
            uid = reply.sender_id

        if not uid:
            await event.edit("❌ ریپلای یا آیدی بده")
            return

        try:
            await client(BlockRequest(uid))
            await event.edit(f"⛔ کاربر {uid} بلاک شد")
        except Exception as e:
            await event.edit(f"❌ خطا: {e}")

    # --- آیدی
    @client.on(events.NewMessage(pattern=r"^.آیدی$"))
    async def get_id(event):
        if not is_owner(event):
            return
        target = await event.get_sender()
        if event.is_reply:
            reply = await event.get_reply_message()
            target = await reply.get_sender()
        uid = target.id
        name = (getattr(target, "first_name", None) or "").strip()
        uname = f"@{target.username}" if getattr(target, "username", None) else "ندارد"
        link = f"tg://user?id={uid}"

        txt = (
            f"👤 نام: {name}\n"
            f"🆔 آیدی: `{uid}`\n"
            f"🔗 یوزرنیم: {uname}\n"
            f"🔗 لینک: {link}"
        )
        await event.edit(txt)

    # --- تاریخ
    @client.on(events.NewMessage(pattern=r"^.تاریخ$"))
    async def show_date(event):
        if not is_owner(event):
            return
        iran = pytz.timezone("Asia/Tehran")
        now = datetime.now(iran)
        g = now.strftime("%Y.%m.%d %H:%M:%S")
        sh = jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        await event.edit(f"📆 امروز:\n🗓 میلادی: {g}\n📆 شمسی: {sh}")

    # --- واکنش (تنظیم)
    @client.on(events.NewMessage(pattern=r"^.واکنش (.+)$"))
    async def set_react(event):
        if not is_owner(event):
            return
        if not event.is_reply:
            await event.edit("❌ روی پیام ریپلای کن!")
            return
        emoji = event.pattern_match.group(1).strip()
        reply = await event.get_reply_message()
        user = await reply.get_sender()

        state.setdefault("react_users", {})
        state["react_users"][user.id] = emoji
        save_state()
        await event.edit(f"✅ از حالا روی پیام‌های {getattr(user, 'first_name', 'کاربر')} ری‌اکشن {emoji} می‌زنم.")

    # --- هندلر ری‌اکشن اتوماتیک
    @client.on(events.NewMessage)
    async def auto_react(event):
        reacts = state.get("react_users")
        if not reacts:
            return
        emoji = reacts.get(event.sender_id)
        if not emoji:
            return

        try:
            await client(
                SendReactionRequest(
                    peer=event.chat_id,
                    msg_id=event.message.id,
                    reaction=[ReactionEmoji(emoticon=emoji)],
                    big=False,
                    add_to_recent=True,
                )
            )
        except Exception:
            pass