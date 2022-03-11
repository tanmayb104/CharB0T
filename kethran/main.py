# coding=utf-8
import logging
import os
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands
from dotenv import load_dotenv


# noinspection PyBroadException
def main():
    """Main"""
    if os.name != "nt":
        import uvloop

        uvloop.install()

    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARNING)
    handler = RotatingFileHandler(
        filename="kethran.log",
        encoding="utf-8",
        mode="w",
        maxBytes=2000000,
        backupCount=10,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    logger.addHandler(handler)
    bot = commands.Bot(
        command_prefix="k",
        owner_id=363095569515806722,
        case_insensitive=True,
        help_command=None,
        intents=discord.Intents.all(),
    )

    async def on_connect():
        """Function called on bot connect"""
        print("Logged In!")

    bot.on_connect = on_connect
    bot.load_extension("jishaku")
    bot.load_extension("primary")
    load_dotenv()
    bot.run(os.getenv("Token"))


if __name__ == "__main__":
    main()