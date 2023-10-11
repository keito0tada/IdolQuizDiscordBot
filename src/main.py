import random
import logging
import json, os
import discord
import gspread
from google.oauth2.service_account import Credentials
from discord.ext import commands
from .UtilityClasses_DiscordBot import base

class ImageSender(base.Command):
    def __init__(self, bot: discord.ext.commands.Bot, allow_duplicated=False):
        logging.info('idolquiz init')
        super().__init__(bot, allow_duplicated)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_env = os.getenv('GOOGLE_CREDENTIALS')
        if creds_env is None:
            creds = Credentials.from_service_account_file(
                "credentials.json",
                scopes=scope
            )
        else:
            creds = Credentials.from_service_account_info(
                json.load(creds_env),
                scopes=scope
            )
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1-V7uZEYEXVG87a_OT9y5QE3PTltOZin0HnnY3iaDJJw/edit?usp=sharing"
        self.workbook = client.open_by_url(url)

    @commands.command()
    async def nogizaka(self, ctx: commands.Context):
        member_list = self.workbook.worksheets()[0].get_all_values()
        member_image_list = self.workbook.worksheets()[1].get_all_values() 
        index = random.randint(0, len(member_image_list) - 1)
        member = next(filter(lambda x: x[0] == member_image_list[index][0], member_list), '')
        embed = discord.Embed(title=member_image_list[index][0], description='{}期'.format(member[1]))
        embed.set_image(url=member_image_list[index][1])
        await ctx.channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ImageSender(bot=bot))