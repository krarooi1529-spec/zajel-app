import os
import random
import html
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LabeledPrice,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)

# =========================================================
# إعدادات البوت ومعلومات المطور
# =========================================================

TOKEN = "8088206300:AAE7zNcR_QRS-Ay7W-fI0M0-5ODk3xNgVf8"
BOT_USERNAME = "ouewuibot"
DEVELOPER_ID = 8468441413

CHANNEL_LINK = "https://t.me/lb_saw"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================================================
# قائمة الأحكام للروليت السريع
# =========================================================

AHKAM_LIST = [
    "غير صورتك الشخصية لمدة 24 ساعة.",
    "اكتب في النبذه: خطبت 😭.",
    "أرسل بصمة صوتية تغني فيها.",
    "غير اسمك لمدة يوم كامل.",
    "نفذ طلب الي سوا الروليت.",
    "قول انا سمكه 5 مرات",
]

# =========================================================
# قاعدة البيانات المؤقتة بالذاكرة وتفضيلات الإشعارات
# =========================================================

games = {}
inline_games = {}
user_channels = {}
user_states = {}
creation_data = {}

all_users = set()
forced_sub_channel = None

# إعدادات الإشعارات (متغيرات التحكم)
NOTIFY_NEW_JOIN = True
NOTIFY_BOT_BLOCK = True

# =========================================================
# أدوات الأزرار الملونة
# =========================================================

def btn(text, callback_data=None, url=None, share_query=None, style=None):
    kwargs = {"text": text}
    if share_query is not None:
        kwargs["switch_inline_query"] = share_query
    elif callback_data is not None:
        kwargs["callback_data"] = callback_data

    if url is not None:
        kwargs["url"] = url
    if style is not None:
        kwargs["style"] = style

    return InlineKeyboardButton(**kwargs)

def primary(text, callback_data=None, share_query=None):
    return btn(text, callback_data=callback_data, share_query=share_query, style="primary")

def success(text, callback_data=None, share_query=None):
    return btn(text, callback_data=callback_data, share_query=share_query, style="success")

def danger(text, callback_data=None, share_query=None):
    return btn(text, callback_data=callback_data, share_query=share_query, style="danger")

def url_button(text, url):
    return btn(text, url=url, style="primary")

# =========================================================
# التحقق من الاشتراك الإجباري العام
# =========================================================

async def check_forced_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not forced_sub_channel:
        return True
    try:
        member = await context.bot.get_chat_member(forced_sub_channel, user_id)
        if member.status in ("member", "administrator", "creator"):
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking forced sub: {e}")
        return True

# =========================================================
# القوائم الرئيسية
# =========================================================

def main_keyboard(user_id: int):
    kbd = [
        [primary("روليت عادي", "roulette_normal")],
        [primary("⚖️ روليت أحكام", "roulette_rules")],
        [primary("روليت مميز", "roulette_special")],
        [primary("انشاء مسابقة🏅", "contest_big")],
        [primary("فائدة البوت", "bot_benefit")],
        [success("⭐ ادعمنا", "support_us")],
        [url_button("📢 قناتنا", CHANNEL_LINK)],
    ]
    if user_id == DEVELOPER_ID:
        kbd.append([danger("⚙️ لوحة تحكم الأدمن الاحترافية", "admin_panel")])
    return InlineKeyboardMarkup(kbd)

# =========================================================
# /start & Deep Linking
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)

    if context.args and context.args[0] == "reset":
        message_text = "🔄 <b>تم العودة للقائمة الرئيسية لبدء جولة جديدة!</b>\n\nاختر من القائمة أدناه:"
        user_states[user_id] = None
        if update.callback_query:
            await update.callback_query.edit_message_text(text=message_text, reply_markup=main_keyboard(user_id), parse_mode="HTML")
        else:
            await update.message.reply_text(text=message_text, reply_markup=main_keyboard(user_id), parse_mode="HTML")
        return

    if not await check_forced_sub(user_id, context):
        ch_clean = forced_sub_channel.replace("@", "")
        await update.message.reply_text(
            f"⚠️ <b>يجب عليك الاشتراك في قناة البوت لاستخدامه:</b>\n\n{forced_sub_channel}",
            reply_markup=InlineKeyboardMarkup([
                [url_button("📢 اشترك الآن", f"https://t.me/{ch_clean}")],
                [primary("✅ تحققت من الاشتراك", "check_my_sub")]
            ]),
            parse_mode="HTML"
        )
        return

    user_states[user_id] = None
    user_first_name = html.escape(update.effective_user.first_name or "صديقي")
    message_text = f"🎭 أهلاً بك <b>{user_first_name}</b> في بوت الروليت الاحترافي 🎭\n\nاختر من القائمة أدناه لبدء اللعب أو إنشاء مسابقتك:"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=main_keyboard(user_id),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=main_keyboard(user_id),
            parse_mode="HTML"
        )

async def handle_check_my_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await check_forced_sub(query.from_user.id, context):
        await start(update, context)
    else:
        await query.answer("❌ لم تشترك بعد! يرجى الاشتراك ثم المحاولة.", show_alert=True)

# =========================================================
# لوحة تحكم الأدمن الاحترافية مع التحكم بالإشعارات
# =========================================================

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != DEVELOPER_ID:
        await query.answer("عذراً، هذا القسم للمطور فقط!", show_alert=True)
        return

    await query.answer()
    total_channels = sum(len(v) for v in user_channels.values())
    
    status_join = "✅" if NOTIFY_NEW_JOIN else "❌"
    status_block = "✅" if NOTIFY_BOT_BLOCK else "❌"

    text = (
        "⚙️ <b>لوحة تحكم الأدمن الاحترافية</b>\n\n"
        f"👥 إجمالي عدد المستخدمين: <b>{len(all_users)}</b>\n"
        f"📢 إجمالي القنوات المضافة: <b>{total_channels}</b>\n"
        f"🎡 إجمالي الروليتات النشطة: <b>{len(games)}</b>\n"
        f"📢 قناة الاشتراك الإجباري الحالية: <b>{forced_sub_channel or 'لا يوجد'}</b>"
    )
    
    kbd = InlineKeyboardMarkup([
        [primary(f"🔔 إشعار دخول شخص للروليت: {status_join}", "toggle_join_notify")],
        [primary(f"🚫 إشعار حظر/ترك البوت: {status_block}", "toggle_block_notify")],
        [primary("📢 إرسال إذاعة عامة", "admin_broadcast")],
        [primary("🔒 تعيين قناة اشتراك إجباري", "admin_set_forced_sub")],
        [danger("🔙 العودة للقائمة الرئيسية", "back_to_start")]
    ])
    
    if query.message:
        await query.edit_message_text(text, reply_markup=kbd, parse_mode="HTML")
    else:
        await query.message.reply_text(text, reply_markup=kbd, parse_mode="HTML")

async def handle_toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    global NOTIFY_NEW_JOIN, NOTIFY_BOT_BLOCK
    
    if query.data == "toggle_join_notify":
        NOTIFY_NEW_JOIN = not NOTIFY_NEW_JOIN
        state_text = "مفعل ✅" if NOTIFY_NEW_JOIN else "معطل ❌"
        await query.answer(f"إشعار دخول الروليت أصبح: {state_text}")
    elif query.data == "toggle_block_notify":
        NOTIFY_BOT_BLOCK = not NOTIFY_BOT_BLOCK
        state_text = "مفعل ✅" if NOTIFY_BOT_BLOCK else "معطل ❌"
        await query.answer(f"إشعار حظر البوت أصبح: {state_text}")
        
    await handle_admin_panel(update, context)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != DEVELOPER_ID:
        return
    await query.answer()

    if query.data == "admin_broadcast":
        user_states[user_id] = "waiting_for_broadcast"
        await query.edit_message_text("📝 <b>أرسل الآن نص الإذاعة للجميع:</b>", parse_mode="HTML")
    elif query.data == "admin_set_forced_sub":
        user_states[user_id] = "waiting_for_forced_sub"
        await query.edit_message_text("📢 <b>أرسل معرف القناة (مثال: @my_channel) أو اكتب (الغاء):</b>", parse_mode="HTML")

# =========================================================
# رصد تتبع الحظر والدخول (ChatMemberHandler)
# =========================================================

async def track_bot_blocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_member = update.chat_member
        if not chat_member:
            return
        
        new_status = chat_member.new_chat_member.status
        user = chat_member.from_user
        
        if NOTIFY_BOT_BLOCK and new_status in ("kicked", "left") and chat_member.chat.type == "private":
            user_name = html.escape(user.first_name or "مستخدم")
            await context.bot.send_message(
                chat_id=DEVELOPER_ID,
                text=f"🚫 <b>تنبيه: قام المستخدم بحظر البوت أو مغادرته!</b>\n\n"
                     f"👤 الاسم: <a href='tg://user?id={user.id}'>{user_name}</a>\n"
                     f"🆔 الآيدي: <code>{user.id}</code>",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error in track_bot_blocks: {e}")

# =========================================================
# الروليت العادي والأحكام والمسابقات
# =========================================================

async def handle_normal_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = None

    text = (
        "🪩 <b>تم اختيار الروليت العادي</b>\n\n"
        "اضغط على الزر أدناه لبدء اللعب ومشاركته مع أصدقائك:"
    )
    keyboard = InlineKeyboardMarkup([
        [primary("ابدأ الآن 🎭", share_query="normal")],
        [danger("🏠 رجوع", "back_to_start")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def handle_rules_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = None

    text = (
        "📜 <b>تم اختيار روليت الأحكام</b>\n\n"
        "اضغط على الزر أدناه لبدء اللعب ومشاركته مع أصدقائك:"
    )
    keyboard = InlineKeyboardMarkup([
        [primary("ابدأ الآن 🎭", share_query="hakam")],
        [danger("🏠 رجوع", "back_to_start")]
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

async def handle_big_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [danger("🔙 العودة للقائمة الرئيسية", "back_to_start")],
    ])
    await query.edit_message_text(
        "❌ القسم تحت الصيانة",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

async def handle_support_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stars_keyboard = [
        [
            success("⭐ 2", "donate_stars_2"),
            success("⭐ 5", "donate_stars_5"),
            success("⭐ 10", "donate_stars_10"),
        ],
        [
            success("⭐ 25", "donate_stars_25"),
            success("⭐ 50", "donate_stars_50"),
            success("⭐ 100", "donate_stars_100"),
        ],
        [danger("🔙 رجوع", "back_to_start")],
    ]
    await query.edit_message_text(
        "⭐ <b>دعم البوت</b>\n\nاختر عدد النجوم التي تود التبرع بها لدعم المطور والخدمة:",
        reply_markup=InlineKeyboardMarkup(stars_keyboard),
        parse_mode="HTML",
    )

async def handle_stars_donation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("تم إرسال فاتورة الدفع ⭐")
    stars_amount = int(query.data.replace("donate_stars_", ""))
    try:
        await context.bot.send_invoice(
            chat_id=query.from_user.id,
            title="دعم البوت",
            description=f"تبرع بـ {stars_amount} نجمة",
            payload=f"stars_donation_{stars_amount}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(f"تبرع بـ {stars_amount} نجمة", stars_amount)],
        )
    except Exception as e:
        logging.error(f"Invoice error: {e}")
        await query.message.reply_text("❌ تعذر إرسال فاتورة النجوم.")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("شكراً جزيلاً على دعمك المتميز! ⭐️❤️")

async def handle_bot_benefit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    benefit_text = (
        "🖇 <b>معلومات شاملة عن البوت</b>\n\n"
        "<blockquote expandable>"
        "🪽 <b>فكرة البوت وفائدته:</b>\n"
        "يعتبر هذا البوت الأداة الأقوى والأسرع في التليجرام لإدارة المسابقات التفاعلية...\n"
        "</blockquote>\n\n"
        "🗯 <b>صُنع هذا العمل بدقة واحرافية بواسطة:</b> @oeow1"
    )
    
    keyboard = InlineKeyboardMarkup([[danger("🔙 العودة للقائمة الرئيسية", "back_to_start")]])
    await query.edit_message_text(text=benefit_text, reply_markup=keyboard, parse_mode="HTML")

# =========================================================
# نظام الـ Inline Mode (مع حصر تدوير العجلة لصاحب الروليت)
# =========================================================

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    is_hakam = "hakam" in query_text.lower()
    
    if is_hakam:
        title_text = "روليت أحكام"
        desc_text = "دوس حته تلعب (مع إعطاء حكم للفائز)"
        content_header = "📜 <b>روليت أحكام</b>"
        btn_j = f"ijoin_hakam_{user_id}"
        btn_s = f"ispin_hakam_{user_id}"
    else:
        title_text = "روليت عادي"
        desc_text = "دوس حته تلعب"
        content_header = "🎰 <b>روليت عادي</b>"
        btn_j = f"ijoin_normal_{user_id}"
        btn_s = f"ispin_normal_{user_id}"

    results = [
        InlineQueryResultArticle(
            id="ir_roulette_game",
            title=title_text,
            description=desc_text,
            input_message_content=InputTextMessageContent(
                f"{content_header} عبر @{BOT_USERNAME}\n\n"
                f"👤 المشاركين: 0\n"
                f"🏆 لم يتم اختيار الفائز بعد",
                parse_mode="HTML"
            ),
            reply_markup=InlineKeyboardMarkup([
                [success("انقر للانضمام 🎯", btn_j)],
                [danger("تدوير العجلة 🎡", btn_s)]
            ])
        )
    ]
    await update.inline_query.answer(results, cache_time=1)

async def handle_inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    msg_id = query.inline_message_id

    if not msg_id:
        return

    if msg_id not in inline_games:
        inline_games[msg_id] = {"players": [], "type": "normal"}

    game = inline_games[msg_id]

    parts = data.split("_")
    game_type = "hakam" if "hakam" in data else "normal"
    owner_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

    if data.startswith("ijoin_"):
        game["type"] = game_type

        if any(p["id"] == user.id for p in game["players"]):
            await query.answer("أنت منضم بالفعل!", show_alert=True)
            return

        user_name = html.escape(user.first_name or "مشارك")
        user_link = f'<a href="tg://user?id={user.id}">{user_name}</a>'
        game["players"].append({"id": user.id, "link": user_link})
        
        await query.answer("تم انضمامك بنجاح! ✅")

        title = "روليت أحكام" if game_type == "hakam" else "روليت عادي"
        players_list = "\n".join([f"• المشارك ({i+1}): {p['link']}" for i, p in enumerate(game["players"])])
        
        owner_id_str = str(owner_id) if owner_id else ""
        btn_j = f"ijoin_hakam_{owner_id_str}" if game_type == "hakam" else f"ijoin_normal_{owner_id_str}"
        btn_s = f"ispin_hakam_{owner_id_str}" if game_type == "hakam" else f"ispin_normal_{owner_id_str}"

        await query.edit_message_text(
            f"🎰 <b>{title}</b> عبر @{BOT_USERNAME}\n\n"
            f"👤 المشاركين: {len(game['players'])}\n"
            f"🏆 لم يتم اختيار الفائز بعد\n\n"
            f"📋 <b>قائمة المشاركين:</b>\n{players_list}",
            reply_markup=InlineKeyboardMarkup([
                [success("انقر للانضمام 🎯", btn_j)],
                [danger("تدوير العجلة 🎡", btn_s)]
            ]),
            parse_mode="HTML"
        )
        return

    if data.startswith("ispin_"):
        if owner_id and user.id != owner_id:
            await query.answer("عذراً، فقط الشخص الذي قام بنشر الروليت يمكنه تدوير العجلة!", show_alert=True)
            return

        if not game["players"]:
            await query.answer("لا يوجد مشاركون لتدوير العجلة!", show_alert=True)
            return

        winner = random.choice(game["players"])
        players_list = "\n".join([f"• المشارك ({i+1}): {p['link']}" for i, p in enumerate(game["players"])])
        reset_url = f"https://t.me/{BOT_USERNAME}?start=reset"

        if "hakam" in data or game["type"] == "hakam":
            hakam = random.choice(AHKAM_LIST)
            res_text = (
                f"📜 <b>روليت أحكام</b> عبر @{BOT_USERNAME}\n\n"
                f"🏆 <b>الفائز هو:</b> {winner['link']}\n"
                f"⚖️ <b>الحكم المطلوب منه:</b> {hakam}\n\n"
                f"📋 <b>قائمة المشاركين ({len(game['players'])}):</b>\n{players_list}"
            )
        else:
            res_text = (
                f"🎰 <b>روليت عادي</b> عبر @{BOT_USERNAME}\n\n"
                f"🏆 <b>الفائز هو:</b> {winner['link']}\n\n"
                f"📋 <b>قائمة المشاركين ({len(game['players'])}):</b>\n{players_list}"
            )

        await query.edit_message_text(
            res_text,
            reply_markup=InlineKeyboardMarkup([
                [url_button("اللعب مجدداً 🔄", reset_url)],
                [url_button("قناتنا 📢", CHANNEL_LINK)]
            ]),
            parse_mode="HTML"
        )
        await query.answer("تم السحب بنجاح! 🎉")
        return

# =========================================================
# الروليت المميز وإدارة القنوات (التحقق من الإشراف قبل الإنشاء والنشر)
# =========================================================

async def handle_special_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = None

    text = "🎨 <b>الروليت المميز الاحترافي</b>\n\nقم بإنشاء روليت مخصص بشروط حماية واشتراك إجباري ونشره بقنواتك."
    special_keyboard = [
        [primary("➕ بدء إنشاء روليت", "create_special_roulette")],
        [primary("📢 إعدادات القنوات", "channels_settings")],
        [primary("💎 الشروط والأسعار", "buy_conditions")],
        [danger("🔙 العودة للقائمة", "back_to_start")],
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(special_keyboard), parse_mode="HTML")

async def handle_buy_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [success("⭐ دعم بالنجوم", "support_us")],
        [danger("🔙 رجوع", "roulette_special")],
    ])
    await query.edit_message_text("💎 <b>الميزات والشروط:</b>\n\nالبوت مجاني بالكامل ويمكنك دعمه بالنجوم للتطوير المستمر.", reply_markup=keyboard, parse_mode="HTML")

async def handle_start_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    user_states[user_id] = "waiting_for_title"
    creation_data[user_id] = {
        "forced_channels": [],
        "is_protected": False
    }

    keyboard = InlineKeyboardMarkup([[danger("❌ إلغاء", "roulette_special")]])
    await query.edit_message_text("📝 <b>أرسل الآن عنوان المسابقة:</b>", reply_markup=keyboard, parse_mode="HTML")

async def handle_unlimited_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in creation_data:
        creation_data[user_id] = {"forced_channels": [], "is_protected": False}

    creation_data[user_id]["max_participants"] = "∞"
    user_states[user_id] = "waiting_for_winners_count"
    await query.edit_message_text("🏆 <b>أرسل عدد الفائزين في هذا السحب:</b>", parse_mode="HTML")

async def ask_roulette_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [primary("📢 شرط الاشتراك بقناة واحدة", "req_single_channel")],
        [danger("❌ تخطي (بدون شروط)", "req_skip_conditions")],
    ])
    await update.message.reply_text("⚖️ <b>هل تريد إضافة شروط للمشاركة في الروليت؟</b>", reply_markup=keyboard, parse_mode="HTML")

async def handle_req_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "req_skip_conditions":
        await ask_final_channel_publish(query, user_id)
    elif query.data == "req_single_channel":
        user_states[user_id] = "waiting_for_req_channel"
        await query.edit_message_text(
            "📢 <b>أرسل الآن معرف القناة المشروطة (مثال: lodjq أو @lodjq):</b>\nتأكد من رفع البوت مشرفاً فيها أولاً.",
            parse_mode="HTML"
        )

async def ask_final_channel_publish(query_or_update, user_id):
    channels = user_channels.get(user_id, [])
    is_callback = hasattr(query_or_update, "edit_message_text")

    keyboard = []
    for ch in channels:
        ch_title = html.escape(ch.get("title", "قناة"))
        keyboard.append([primary(f"📢 {ch_title}", f"publish_to_{ch['id']}")])
        
    keyboard.append([primary("➕ إضافة قناة جديدة", "add_channel_for_publish")])
    keyboard.append([danger("🔙 رجوع", "roulette_special")])

    text = "🎯 <b>اختر القناة لنشر المسابقة:</b>"
    
    if is_callback:
        await query_or_update.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await query_or_update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

async def handle_channels_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = None
    channels = user_channels.get(user_id, [])

    if not channels:
        text = "📢 <b>إدارة القنوات</b>\n\nلا توجد قنوات مضافة حالياً."
    else:
        text = "📢 <b>إدارة القنوات الخاصة بك:</b>\n\n"
        for idx, ch in enumerate(channels, 1):
            title = html.escape(ch["title"] or "بدون اسم")
            username = html.escape(ch["username"])
            text += f"{idx}. {title} ({username})\n"

    channels_keyboard = [
        [primary("➕ إضافة قناة جديدة", "add_new_channel")],
        [danger("🔙 رجوع", "roulette_special")],
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(channels_keyboard), parse_mode="HTML")

async def handle_add_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = "waiting_for_channel"
    keyboard = InlineKeyboardMarkup([[danger("🔙 رجوع", "channels_settings")]])
    await query.edit_message_text(
        "📢 <b>أرسل معرف القناة</b>\nمثال: <code>@my_channel</code>\n\n⚠️ يجب أن تكون أنت مشرفاً (أو منشئاً) في القناة والبوت مشرفاً فيها أيضاً.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

async def handle_add_channel_for_publish_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = "waiting_for_publish_channel"
    await query.edit_message_text(
        "📢 <b>أرسل الآن معرف القناة لنشر المسابقة فيها مباشرة:</b>\nمثال: <code>@my_channel</code>\n\n⚠️ تأكد من رفع البوت مشرفاً فيها أولاً.",
        parse_mode="HTML"
    )

# =========================================================
# معالجة الإدخالات النصية
# =========================================================

async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)
    text = (update.message.text or "").strip()

    if not text:
        return

    if state == "waiting_for_broadcast" and user_id == DEVELOPER_ID:
        user_states[user_id] = None
        sent, failed = 0, 0
        for uid in list(all_users):
            try:
                await context.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"✅ تمت الإذاعة بنجاح:\nتم الإرسال: {sent}\nفشل: {failed}")
        return

    if state == "waiting_for_forced_sub" and user_id == DEVELOPER_ID:
        user_states[user_id] = None
        global forced_sub_channel
        if text == "الغاء":
            forced_sub_channel = None
            await update.message.reply_text("تم إلغاء الاشتراك الإجباري العام.")
        else:
            forced_sub_channel = text if text.startswith("@") else f"@{text}"
            await update.message.reply_text(f"تم ضبط قناة الاشتراك الإجباري: {forced_sub_channel}")
        return

    if state == "waiting_for_channel" or state == "waiting_for_publish_channel":
        channel_username = text if text.startswith("@") else f"@{text}"
        try:
            chat = await context.bot.get_chat(channel_username)
            if chat.type != "channel":
                await update.message.reply_text("❌ هذا المعرف لا يعود إلى قناة.")
                return

            # التحقق المشدد: هل المستخدم الحالي مشرف أو منشئ في القناة؟
            try:
                user_member = await context.bot.get_chat_member(chat.id, user_id)
                if user_member.status not in ("administrator", "creator"):
                    await update.message.reply_text("❌ تأكد بأنك مشرف في تلك القناة")
                    return
            except Exception:
                await update.message.reply_text("❌ تأكد بأنك مشرف في تلك القناة")
                return

            # التحقق من صلاحيات البوت
            bot_info = await context.bot.get_me()
            try:
                bot_member = await context.bot.get_chat_member(chat.id, bot_info.id)
                if bot_member.status not in ("administrator", "creator"):
                    await update.message.reply_text("❌ البوت ليس مشرفاً في القناة.")
                    return
            except Exception:
                await update.message.reply_text("❌ البوت ليس مشرفاً في القناة أو لا يمكنه التحقق من صلاحياته.")
                return

            if user_id not in user_channels:
                user_channels[user_id] = []

            if not any(c["id"] == chat.id for c in user_channels[user_id]):
                user_channels[user_id].append({
                    "id": chat.id,
                    "title": chat.title or "بدون اسم",
                    "username": channel_username,
                })

            if state == "waiting_for_channel":
                user_states[user_id] = None
                await update.message.reply_text(
                    f"تمت إضافة القناة بنجاح: <b>{html.escape(chat.title or 'بدون اسم')}</b> ✅",
                    reply_markup=InlineKeyboardMarkup([[primary("📢 إدارة القنوات", "channels_settings")]]),
                    parse_mode="HTML"
                )
            else:
                user_states[user_id] = None
                await publish_game_to_chat(update, context, user_id, chat.id)
        except Exception as e:
            logging.error(f"Error adding channel: {e}")
            await update.message.reply_text("❌ تأكد بأنك مشرف في تلك القناة")
        return

    if state == "waiting_for_title":
        creation_data[user_id]["title"] = text
        user_states[user_id] = "waiting_for_max_participants"
        keyboard = InlineKeyboardMarkup([
            [primary("♾️ بدون حد أقصى", "unlimited_participants")],
            [danger("❌ إلغاء", "roulette_special")],
        ])
        await update.message.reply_text("👥 <b>أرسل الحد الأقصى للمشاركين:</b>", reply_markup=keyboard, parse_mode="HTML")
        return

    if state == "waiting_for_max_participants":
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح أكبر من صفر.")
            return
        creation_data[user_id]["max_participants"] = text
        user_states[user_id] = "waiting_for_winners_count"
        await update.message.reply_text("🏆 <b>أرسل عدد الفائزين في هذا السحب:</b>", parse_mode="HTML")
        return

    if state == "waiting_for_winners_count":
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح أكبر من صفر.")
            return
        creation_data[user_id]["winners_count"] = text
        user_states[user_id] = None
        await ask_roulette_protection(update, context)
        return

    if state == "waiting_for_req_channel":
        ch_user = text if text.startswith("@") else f"@{text}"
        try:
            chat = await context.bot.get_chat(ch_user)
            bot_info = await context.bot.get_me()
            member = await context.bot.get_chat_member(chat.id, bot_info.id)
            
            if member.status not in ("administrator", "creator"):
                await update.message.reply_text("❌ البوت موجود في القناة لكنه ليس مشرفاً! يرجى رفعه مشرفاً أولاً.")
                return

            creation_data[user_id]["req_channel"] = ch_user
            creation_data[user_id]["req_channel_id"] = chat.id
            user_states[user_id] = None
            
            if user_id not in user_channels:
                user_channels[user_id] = []
            if not any(c["id"] == chat.id for c in user_channels[user_id]):
                user_channels[user_id].append({
                    "id": chat.id,
                    "title": chat.title or ch_user,
                    "username": ch_user,
                })

            await ask_final_channel_publish(update, user_id)
        except Exception as e:
            logging.error(f"Error checking req channel: {e}")
            await update.message.reply_text(
                "❌ <b>تعذر العثور على القناة أو التأكد من الصلاحيات!</b>",
                parse_mode="HTML"
            )
        return

# =========================================================
# نشر المسابقة وتفاعلات القناة
# =========================================================

def build_game_text(game, bot_username):
    current_count = len(game["participants"])
    title = html.escape(str(game["title"]))
    max_p = html.escape(str(game["max"]))
    winners = html.escape(str(game["winners"]))
    req_ch = game.get("req_channel")

    req_str = f"\nشرط المشاركة: الإشترك في {req_ch}" if req_ch else ""

    return (
        f"<b>{title}</b>\n\n"
        f"👥 <b>عدد المشاركين:</b> {current_count}/{max_p}\n"
        f"🏆 <b>عدد الفائزين:</b> {winners}"
        f"{req_str}\n\n"
        f'<a href="https://t.me/{bot_username}">رؤية السحوبات | بوت الروليت</a>'
    )

def build_custom_roulette_keyboard(game_id, current_p_count):
    return InlineKeyboardMarkup([
        [success(f"مشاركة ({current_p_count})", f"cjoin_{game_id}")],
        [
            danger("🎡 تدوير العجلة", f"cspin_{game_id}"),
            primary("🔄 اعادة نشر", f"repost_{game_id}"),
        ],
        [url_button("قناتنا", CHANNEL_LINK)]
    ])

async def publish_game_to_chat(update, context, user_id, chat_id):
    msg_obj = update.message if update.message else update.callback_query.message

    # التحقق الإجباري الحاسم قبل النشر
    try:
        user_member = await context.bot.get_chat_member(chat_id, user_id)
        if user_member.status not in ("administrator", "creator"):
            await msg_obj.reply_text("❌ تأكد بأنك مشرف في تلك القناة")
            return
    except Exception:
        await msg_obj.reply_text("❌ تأكد بأنك مشرف في تلك القناة")
        return

    data = creation_data.get(user_id, {})
    game_id = f"g_{random.randint(10000, 99999)}"

    games[game_id] = {
        "owner_id": user_id,
        "title": data.get("title", "روليت"),
        "max": data.get("max_participants", "50"),
        "winners": data.get("winners_count", "1"),
        "req_channel": data.get("req_channel"),
        "req_channel_id": data.get("req_channel_id"),
        "participants": {},
        "chat_id": chat_id,
        "msg_id": None
    }

    bot_info = await context.bot.get_me()
    post_text = build_game_text(games[game_id], bot_info.username)
    keyboard = build_custom_roulette_keyboard(game_id, 0)

    try:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=post_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        games[game_id]["msg_id"] = msg.message_id
        creation_data.pop(user_id, None)

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ <b>تم نشر الروليت في القناة بنجاح!</b>",
            reply_markup=main_keyboard(user_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error sending message to channel: {e}")
        await msg_obj.reply_text("❌ تأكد بأنك مشرف في تلك القناة")

async def handle_publish_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = int(query.data.replace("publish_to_", ""))
    await publish_game_to_chat(update, context, user_id, chat_id)

async def update_game_message(context, game_id):
    game = games.get(game_id)
    if not game or not game.get("msg_id"):
        return
    bot_info = await context.bot.get_me()
    post_text = build_game_text(game, bot_info.username)
    keyboard = build_custom_roulette_keyboard(game_id, len(game["participants"]))
    try:
        await context.bot.edit_message_text(
            chat_id=game["chat_id"],
            message_id=game["msg_id"],
            text=post_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Error updating game msg: {e}")

async def handle_custom_game_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data.startswith("repost_"):
        game_id = data.replace("repost_", "")
        game = games.get(game_id)
        if not game or user.id != game["owner_id"]:
            await query.answer("فقط منشئ المسابقة يمكنه إعادة النشر!", show_alert=True)
            return

        try:
            await context.bot.delete_message(chat_id=game["chat_id"], message_id=game["msg_id"])
        except Exception:
            pass

        bot_info = await context.bot.get_me()
        post_text = build_game_text(game, bot_info.username)
        keyboard = build_custom_roulette_keyboard(game_id, len(game["participants"]))

        new_msg = await context.bot.send_message(
            chat_id=game["chat_id"],
            text=post_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        game["msg_id"] = new_msg.message_id
        await query.answer("تمت إعادة نشر الروليت بنجاح! 🔄")
        return

    if data.startswith("cjoin_"):
        game_id = data.replace("cjoin_", "")
        game = games.get(game_id)

        if not game:
            await query.answer("❌ هذه اللعبة انتهت أو غير متاحة!", show_alert=True)
            return

        req_ch_id = game.get("req_channel_id")
        req_ch_name = game.get("req_channel")

        if req_ch_id or req_ch_name:
            try:
                target_ch = req_ch_id if req_ch_id else req_ch_name
                m = await context.bot.get_chat_member(target_ch, user.id)
                if m.status not in ("member", "administrator", "creator"):
                    await query.answer(f"⚠️ يجب عليك الاشتراك بالقناة المشروطة أولاً ({req_ch_name}) للمشاركة!", show_alert=True)
                    return
            except Exception as e:
                logging.error(f"Error checking channel sub: {e}")

        if game["max"] != "∞" and len(game["participants"]) >= int(game["max"]):
            await query.answer("عذراً، اكتمل عدد المشاركين بالكامل!", show_alert=True)
            return

        if user.id in game["participants"]:
            await query.answer("أنت مشارك بالفعل في هذا الروليت! 👍", show_alert=True)
            return

        user_name = html.escape(user.first_name or "مستخدم")
        user_link = f'<a href="tg://user?id={user.id}">{user_name}</a>'
        game["participants"][user.id] = user_link

        if NOTIFY_NEW_JOIN:
            try:
                await context.bot.send_message(
                    chat_id=DEVELOPER_ID,
                    text=f"👤 <b>انضمام جديد لروليت مميز:</b>\n\n"
                         f"👤 الاسم: {user_link}\n"
                         f"🆔 الآيدي: <code>{user.id}</code>\n"
                         f"📌 الروليت: {game.get('title')}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await query.answer("تم تسجيل مشاركتك بنجاح! 🥳", show_alert=True)
        await update_game_message(context, game_id)
        return

    if data.startswith("cspin_"):
        game_id = data.replace("cspin_", "")
        game = games.get(game_id)

        if not game or user.id != game["owner_id"]:
            await query.answer("فقط منشئ المسابقة يمكنه إجراء السحب!", show_alert=True)
            return

        if len(game["participants"]) == 0:
            await query.answer("لا يوجد مشاركون بعد لتدوير العجلة!", show_alert=True)
            return

        winners_count = int(game["winners"]) if str(game["winners"]).isdigit() else 1
        participant_ids = list(game["participants"].keys())
        selected_ids = random.sample(participant_ids, min(winners_count, len(participant_ids)))

        winners_str = "\n".join(game["participants"][uid] for uid in selected_ids)
        winners_post_text = f"🏆 <b>الفائزون بالمسابقة:</b>\n\n{winners_str}\n\n🎉 <b>مبروك للفائزين!</b>"

        await query.answer("تم السحب بنجاح! 🎡")
        await context.bot.send_message(chat_id=game["chat_id"], text=winners_post_text, parse_mode="HTML")
        return

# =========================================================
# التشغيل الرئيسي
# =========================================================

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_check_my_sub, pattern=r"^check_my_sub$"))

    app.add_handler(InlineQueryHandler(handle_inline_query))
    app.add_handler(CallbackQueryHandler(handle_inline_callback, pattern=r"^(ijoin_|ispin_)"))

    app.add_handler(CommandHandler("admin", handle_admin_panel))
    app.add_handler(CallbackQueryHandler(handle_admin_panel, pattern=r"^admin_panel$"))
    app.add_handler(CallbackQueryHandler(handle_admin_actions, pattern=r"^admin_(broadcast|set_forced_sub)$"))
    
    app.add_handler(CallbackQueryHandler(handle_toggle_notifications, pattern=r"^toggle_(join|block)_notify$"))
    app.add_handler(ChatMemberHandler(track_bot_blocks, ChatMemberHandler.MY_CHAT_MEMBER))

    app.add_handler(CallbackQueryHandler(handle_support_us, pattern=r"^support_us$"))
    app.add_handler(CallbackQueryHandler(handle_stars_donation, pattern=r"^donate_stars_\d+$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    app.add_handler(CallbackQueryHandler(handle_normal_roulette, pattern=r"^roulette_normal$"))
    app.add_handler(CallbackQueryHandler(handle_rules_roulette, pattern=r"^roulette_rules$"))
    app.add_handler(CallbackQueryHandler(handle_special_roulette, pattern=r"^roulette_special$"))
    app.add_handler(CallbackQueryHandler(handle_big_contest, pattern=r"^contest_big$"))
    app.add_handler(CallbackQueryHandler(handle_bot_benefit, pattern=r"^bot_benefit$"))

    app.add_handler(CallbackQueryHandler(handle_start_creation, pattern=r"^create_special_roulette$"))
    app.add_handler(CallbackQueryHandler(handle_unlimited_participants, pattern=r"^unlimited_participants$"))
    app.add_handler(CallbackQueryHandler(handle_req_choice, pattern=r"^req_(single_channel|skip_conditions)$"))
    app.add_handler(CallbackQueryHandler(handle_publish_to_channel, pattern=r"^publish_to_-?\d+$"))
    app.add_handler(CallbackQueryHandler(handle_add_channel_for_publish_prompt, pattern=r"^add_channel_for_publish$"))

    app.add_handler(CallbackQueryHandler(handle_channels_settings, pattern=r"^channels_settings$"))
    app.add_handler(CallbackQueryHandler(handle_add_channel_prompt, pattern=r"^add_new_channel$"))
    app.add_handler(CallbackQueryHandler(handle_buy_conditions, pattern=r"^buy_conditions$"))

    app.add_handler(CallbackQueryHandler(handle_custom_game_actions, pattern=r"^(repost_|cjoin_|cspin_)"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_inputs))
    app.add_handler(CallbackQueryHandler(back_to_start, pattern=r"^back_to_start$"))

    print(f"تم تشغيل البوت @{BOT_USERNAME} بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
