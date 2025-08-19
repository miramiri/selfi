# autocatch.py
import re
import time
from telethon import events

ALLOWED_CMD_PATTERN = re.compile(r'^[\w\s./@#:\-+=!?(),]+$')

def _now_ts():
    return int(time.time())

def register_autocatch(client, state, GLOBAL_GROUPS, save_state, send_status):
    """
    ثبت هندلرهای اتوکچ روی کلاینت
    - auto_groups: فقط اتوکچ
    - copy_groups: اتوکچ + کپی
    """

    # --- واکنش به پیام Character_Catcher_Bot و فوروارد به کالکت
    @client.on(events.NewMessage(from_users=["Character_Catcher_Bot"]))
    async def check_bot(event):
        gid = event.chat_id

        # فقط گروه‌هایی که ثبت شده‌اند
        if gid not in (state.get("auto_groups", []) + state.get("copy_groups", [])):
            return

        text = event.raw_text or ""
        emojis = state.get("stop_emoji") or []

        for e in emojis:
            if text.startswith(e):
                # اتوکچ فعال
                if not state.get("awaiting_collect", False):
                    prev_list = list(state.get("echo_users", []))
                    state["saved_echo_users"] = prev_list
                    state["last_user"] = prev_list[-1] if prev_list else None
                    state["last_group"] = gid
                    state["echo_users"] = []           # توقف موقت کپی
                    state["awaiting_collect"] = True   # منتظر پاسخ کالکت
                    state["last_collect_trigger"] = _now_ts()
                    save_state()
                    await send_status()

                try:
                    await client.forward_messages("@collect_waifu_cheats_bot", event.message)
                except Exception as ex:
                    print(f"⚠️ خطا در فوروارد به کالکت: {ex}")
                break

    # --- پردازش پاسخ از @collect_waifu_cheats_bot
    @client.on(events.NewMessage(from_users=["collect_waifu_cheats_bot"]))
    async def handle_collect(event):
        if not state.get("awaiting_collect", False):
            return

        text = (event.raw_text or "").strip()
        gid = state.get("last_group")
        if not gid:
            state["awaiting_collect"] = False
            save_state()
            return

        acted = False

        # حالت Humanizer
        if "Humanizer:" in text:
            m = re.search(r'Humanizer:\s*([^\r\n]+)', text, re.IGNORECASE)
            if m:
                cmd = m.group(1).strip().strip('`"\'')
                if 0 < len(cmd) <= 200 and ALLOWED_CMD_PATTERN.match(cmd):
                    last_cmd = state.get("last_humanizer_cmd")
                    last_ts = state.get("last_humanizer_ts", 0)
                    now = _now_ts()
                    if cmd != last_cmd or (now - last_ts) > 5:
                        try:
                            await client.send_message(gid, cmd)
                            state["last_humanizer_cmd"] = cmd
                            state["last_humanizer_ts"] = now
                            acted = True
                        except Exception as ex:
                            print(f"⚠️ خطا در ارسال Humanizer: {ex}")

        # حالت گرفتن کاراکتر جدید
        if "got a new character" in text.lower():
            if state.get("last_user"):
                try:
                    await client.send_message(gid, state.get("funny_text", ""))
                except Exception:
                    pass

                # اگر گروه در copy_groups بود → دوباره کپی فعال بشه
                if gid in state.get("copy_groups", []):
                    if state["last_user"] not in state.get("echo_users", []):
                        state["echo_users"].append(state["last_user"])
                        acted = True

                # اگر کپی پلاس فعال بود → خودش دستور .کپی بزنه
                if state.get("copy_plus_user"):
                    try:
                        # ریپلای به پیام آخر کاربر هدف و ارسال .کپی
                        target = state["copy_plus_user"]
                        msgs = await client.get_messages(gid, from_user=target, limit=1)
                        if msgs:
                            await msgs[0].reply(".کپی")
                            acted = True
                    except Exception as ex:
                        print(f"⚠️ خطا در اجرای کپی پلاس: {ex}")

        # پایان چرخه
        state["awaiting_collect"] = False
        state["saved_echo_users"] = []
        save_state()
        if acted:
            await send_status()