import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from handlers.start import router as start_router
from handlers.admin import router as admin_router
from handlers.media import router as media_router
from handlers.inline import router as inline_router
from utils.rate_limiter import RateLimitMiddleware
from utils.user_manager import UserRegisterMiddleware
from utils.subscription_middleware import SubscriptionMiddleware
from utils.history import init_db
from utils.backup import daily_backup_task

async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logging.error("Loyiha uchun BOT_TOKEN o'rnatilmagan! Iltimos, .env faylini tahrirlang.")
        sys.exit(1)

    init_db()
    asyncio.create_task(daily_backup_task())

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.message.outer_middleware(UserRegisterMiddleware())
    dp.message.outer_middleware(SubscriptionMiddleware())
    dp.message.outer_middleware(RateLimitMiddleware())
    dp.callback_query.outer_middleware(SubscriptionMiddleware())

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(inline_router)
    dp.include_router(media_router)

    logging.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni qabul qilmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot faoliyati to'xtatildi.")
