import os
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .nlp import Catalog, detect_intent, background_to_tags, recommend
from .replies import HELP_TEXT, COMPARE_TEXT, OFFTOPIC_TEXT

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN env var")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
catalog = Catalog.load()  # загружаем TF-IDF и курсы


def format_course(row: dict) -> str:
    s = row.get("semester")
    sem = f"семестр {int(s)}" if str(s).isdigit() else "семестр n/a"
    return f"• {row['name']}  <i>({row['program']}, {sem})</i>"

@dp.message(Command("start"))
@dp.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(HELP_TEXT)

@dp.message(Command("compare"))
async def cmd_compare(m: Message):
    await m.answer(COMPARE_TEXT)

@dp.message(Command("plan"))
async def cmd_plan(m: Message, command: CommandObject):
    args = (command.args or "").split()
    if not args:
        await m.answer("Укажите программу: /plan AI или /plan AI_PRODUCT [семестр]")
        return
    prog = args[0].upper()
    sem: Optional[int] = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    df = catalog.df[catalog.df["program"] == prog]
    if sem:
        df = df[df["semester"] == sem]
    if df.empty:
        await m.answer("Не нашёл дисциплины по заданному фильтру.")
        return
    text = f"<b>План {prog}</b>\n" + "\n".join(format_course(r) for _, r in df.iterrows()[:30])
    await m.answer(text)

@dp.message()
async def handle(m: Message):
    text = (m.text or "").strip()
    intent = detect_intent(text)

    if intent == "offtopic":
        await m.answer(OFFTOPIC_TEXT)
        return

    if intent in {"find_course", "fallback"}:
        # пробуем поиск по TF-IDF
        top = catalog.search(text, topk=5)
        if not top:
            await m.answer("Ничего похожего не нашёл в планах программ.")
            return
        resp = "<b>Похожие курсы:</b>\n" + "\n".join(format_course(row) for _, row in top)
        await m.answer(resp)
        return

    if intent == "plan":
        await m.answer('Используйте команду вида: /plan AI 1  — где "AI" или "AI_PRODUCT" и номер семестра опционально.')
        return

    if intent == "compare":
        await m.answer(COMPARE_TEXT)
        return

    if intent == "recommend":
        tags = background_to_tags(text)
        items = recommend(catalog.df, tags, topk=5)
        if not items:
            await m.answer("Не нашёл подходящих элективов.")
            return
        info = "<b>Рекомендовано под ваш бэкграунд ({})</b>\n".format(", ".join(tags))
        info += "\n".join(format_course(r) for r in items)
        await m.answer(info)
        return

if __name__ == "__main__":
    dp.run_polling(bot)
