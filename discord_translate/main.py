# This example requires the 'members' and 'message_content' privileged intents to function.

import asyncio
import io
import os
from typing import List, Optional, TypedDict
import discord
from discord.ext import commands
import aiohttp
import pytesseract
from PIL import Image


description = """Example bot to showcase user apps with translation."""

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="?", description=description, intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    # sync commands
    # await bot.tree.sync()


# TODO: make this a database
LANGUAGE_PREFERENCES = {}


async def ocr(message: discord.Message) -> List[str]:
    ocrd = []

    if message.attachments:
        for attachment in message.attachments:
            att = await attachment.read()
            try:
                image = Image.open(io.BytesIO(att))
            except Exception as e:
                # probably not an image
                continue

            res = await asyncio.get_running_loop().run_in_executor(
                None, pytesseract.image_to_string, image
            )
            while "\n\n" in res:
                res = res.replace("\n\n", "\n")

            ocrd.append(res)

    return ocrd


class DeepLTranslation(TypedDict):
    detected_source_language: str
    text: str


class DeepLResponse(TypedDict):
    translations: List[DeepLTranslation]


async def do_translation(text: List[str], lang: str) -> List[DeepLTranslation]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api-free.deepl.com/v2/translate",
                params={
                    "auth_key": os.environ["DEEPL_KEY"],
                    "target_lang": lang,
                    "text": text,
                },
            ) as response:
                data = await response.json()
                translated_text = data["translations"]
                print(f"Translated {text} - {translated_text}")

    except Exception as e:
        print(e)
        raise e
    else:
        return translated_text


@discord.app_commands.user_install()
@discord.app_commands.allow_contexts(guilds=True, private_channels=True)
@discord.app_commands.context_menu(name="Translate")
async def translate_msg(interaction: discord.Interaction, message: discord.Message):
    """Translate a message"""

    print(
        f"Translating a message from {message.author.name} for {interaction.user.name}"
    )

    preferred_language = LANGUAGE_PREFERENCES.get(interaction.user.id, "en")

    to_translate = []
    if len(message.content.strip()) > 1:
        to_translate.append(message.content)
        has_msg_content = True
    else:
        has_msg_content = False

    image_count = len(to_translate)
    to_translate.extend(await ocr(message))
    image_count = len(to_translate) - image_count

    try:
        translated_text = await do_translation(to_translate, preferred_language)
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to translate :c", ephemeral=True
        )
        print(e)
    else:
        tr_offset = 0
        resp = ""
        if has_msg_content:
            resp += f"Original message ({translated_text[tr_offset]['detected_source_language']}): `{message.content}`\n"
            resp += f"Translated message ({preferred_language}): `{translated_text[tr_offset]['text']}`\n\n"
            tr_offset += 1

        if image_count:
            for i in range(image_count):
                resp += f"Translated image {i + 1} ({translated_text[tr_offset]['detected_source_language']}->{preferred_language}): ```{translated_text[tr_offset+i]['text']}```\n"

        await interaction.response.send_message(resp, ephemeral=True)


bot.tree.add_command(translate_msg)


@discord.app_commands.user_install()
@discord.app_commands.allow_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command()
async def prefer_language(interaction, language: str):
    """Set a preferred language for translation."""
    LANGUAGE_PREFERENCES[interaction.user.id] = language

    await interaction.response.send_message(
        f"Set preferred language to {language}", ephemeral=True
    )


bot.tree.add_command(prefer_language)


@discord.app_commands.user_install()
@discord.app_commands.allow_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.describe(
    text="The text to translate",
    language="Language to translate to",
)
@discord.app_commands.command()
async def translate(interaction, text: str, language: Optional[str] = None):
    """Set a preferred language for translation."""

    preferred_language = language or LANGUAGE_PREFERENCES.get(interaction.user.id, "en")

    try:
        translated_text = await do_translation([text], preferred_language)
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to translate :c", ephemeral=True
        )
        print(e)
    else:
        await interaction.response.send_message(
            f"Translated message ({preferred_language}): `{translated_text[0]['text']}`",
            ephemeral=True,
        )


bot.tree.add_command(translate)

bot.run(os.environ["DISCORD_TOKEN"])
