
import os
import asyncio
import base64
from io import BytesIO

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
HORDE_API = "https://aihorde.net/api/v2"


def generate_image(prompt):
    headers = {
        "apikey": "0000000000",
        "Client-Agent": "ComicBot:1.0:github",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "params": {
            "width": 512,
            "height": 512,
            "steps": 20,
            "n": 1,
        },
        "models": ["stable_diffusion"],
        "r2": False,
    }

    response = requests.post(
        f"{HORDE_API}/generate/async",
        json=payload,
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    job_id = response.json()["id"]

    for _ in range(180):
        status = requests.get(
            f"{HORDE_API}/generate/status/{job_id}",
            headers=headers,
            timeout=30,
        )
        status.raise_for_status()
        data = status.json()

        if data.get("fault"):
            raise RuntimeError("Image generation failed")

        if data.get("done") and data.get("generations"):
            image_data = data["generations"][0]["img"]
            if image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[1]
            return base64.b64decode(image_data)

        import time
        time.sleep(3)

    raise TimeoutError("Image generation took too long")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🎨 Я создаю комиксы из 6 кадров.\n\n"
        "Отправь мне сюжет одним сообщением.\n"
        "Например: Девочка находит волшебный лес."
    )


async def create_comic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    story = update.message.text.strip()

    if len(story) > 1500:
        await update.message.reply_text(
            "Сделай сюжет короче — максимум 1500 символов."
        )
        return

    status = await update.message.reply_text(
        "🎨 Начинаю создавать комикс из 6 кадров. Это может занять время..."
    )

    scenes = [
        "Opening scene: introduce the main character and setting.",
        "The character discovers something unusual.",
        "The character begins an adventure.",
        "An unexpected problem appears.",
        "The character finds a solution.",
        "A satisfying ending to the story.",
    ]

    try:
        for i, scene in enumerate(scenes, start=1):
            prompt = (
                "Create one panel of a coherent six-panel comic. "
                "Colorful detailed comic book illustration, expressive "
                "characters, clear composition, no text, no letters, "
                "no speech bubbles. Keep the same character design. "
                f"Original story: {story}. "
                f"Panel {i} of 6: {scene}"
            )

            image_bytes = await asyncio.to_thread(generate_image, prompt)
            photo = BytesIO(image_bytes)
            photo.name = f"panel_{i}.png"

            await update.message.reply_photo(
                photo=photo,
                caption=f"Кадр {i}/6"
            )

        await status.edit_text(
            "✅ Готово! Все 6 кадров созданы. "
            "Сохрани изображения из чата."
        )

    except Exception as error:
        print("Comic generation error:", repr(error))
        await status.edit_text(
            "Не удалось создать все кадры. Возможно, сервис перегружен. "
            "Попробуй ещё раз позже."
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set the BOT_TOKEN environment variable")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, create_comic)
    )
    app.run_polling()


if __name__ == "__main__":
    main()
