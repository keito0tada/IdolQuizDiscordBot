import random
import logging
import json, os
from typing import Any, Optional
import discord
import random
from discord.interactions import Interaction
import gspread
from google.oauth2.service_account import Credentials
from discord.ext import commands

from cog.IdolQuizDiscordBot.src.UtilityClasses_DiscordBot.base import IWindow, Window
from .UtilityClasses_DiscordBot import base


class QuizWindows(base.Windows):
    class AnswerWindow(base.Window):
        class RetryButton(discord.ui.Button):
            def __init__(self, windows: "QuizWindows"):
                super().__init__(style=discord.ButtonStyle.primary, label="もう一回！")
                self.windows = windows

            async def callback(self, interaction: discord.Interaction):
                await QuizWindows.QuizWindow(windows=self.windows).response_edit(
                    interaction=interaction
                )

        def __init__(
            self,
            windows: "QuizWindows",
            submit_name: str,
            answer_name: str,
            image_url: str,
        ):
            if submit_name == answer_name:
                embed = discord.Embed(
                    title="正解！！", description=submit_name, color=discord.Color.blue()
                ).set_image(url=image_url)
            else:
                embed = discord.Embed(
                    title="不正解！！",
                    description="正解は{}！！".format(answer_name),
                    color=discord.Color.red(),
                ).set_image(url=image_url)
            view = discord.ui.View().add_item(
                QuizWindows.AnswerWindow.RetryButton(windows=windows)
            )
            super().__init__(embed=embed, view=view)

    class QuizWindow(base.Window):
        class MemberNameSelect(discord.ui.Select):
            def __init__(self, member_names: list[str]):
                random.shuffle(member_names)
                super().__init__(
                    options=[
                        discord.SelectOption(label=member_name)
                        for member_name in member_names
                    ]
                )

            async def callback(self, interaction: discord.Interaction) -> None:
                await interaction.response.defer()

        class Submit(discord.ui.Button):
            def __init__(
                self,
                windows: "QuizWindows",
                select: "QuizWindows.QuizWindow.MemberNameSelect",
                answer_name: str,
                image_url: str,
            ):
                super().__init__(style=discord.ButtonStyle.primary, label="決定！")
                self.windows = windows
                self.select = select
                self.answer_name = answer_name
                self.image_url = image_url

            async def callback(self, interaction: discord.Interaction) -> None:
                await QuizWindows.AnswerWindow(
                    windows=self.windows,
                    submit_name=self.select.values[0],
                    answer_name=self.answer_name,
                    image_url=self.image_url,
                ).response_edit(interaction=interaction)

        def __init__(self, windows: "QuizWindows"):
            answer_index = random.randint(0, len(windows.idol_member_columns) - 1)
            answer_name = windows.idol_member_columns[answer_index][0]
            image_columns = [
                column for column in windows.image_columns if column[0] == answer_name
            ]
            problem_index = random.randint(0, len(image_columns) - 1)
            embed = discord.Embed(title="だーれだ？？？").set_image(
                url=image_columns[problem_index][1]
            )
            view = discord.ui.View()
            select = QuizWindows.QuizWindow.MemberNameSelect(
                [answer_name]
                + random.sample(
                    [
                        idol_member_column[0]
                        for idol_member_column in windows.idol_member_columns[
                            :answer_index
                        ]
                        + windows.idol_member_columns[answer_index + 1 :]
                    ],
                    4,
                )
            )
            view.add_item(select)
            view.add_item(
                QuizWindows.QuizWindow.Submit(
                    windows=windows,
                    select=select,
                    answer_name=answer_name,
                    image_url=image_columns[problem_index][1],
                )
            )
            super().__init__(embed=embed, view=view)

    def __init__(self, workbook: gspread.Spreadsheet) -> None:
        self.workbook = workbook
        self.idol_member_columns = workbook.worksheets()[0].get_all_values()
        self.image_columns = workbook.worksheets()[1].get_all_values()
        super().__init__(defaultWindow=QuizWindows.QuizWindow(windows=self))


class GalleryPages(base.Pages):
    def __init__(self, workbook: gspread.Spreadsheet) -> None:
        image_columns = workbook.worksheets()[1].get_all_values()
        for column in image_columns:
            print(column[0])
            print(column[1])
        super().__init__(
            windows=[
                base.Window(
                    embed=discord.Embed(title=column[0]).set_image(url=column[1])
                )
                for column in image_columns
            ],
            defaultIndex=0,
        )


class IdolImageSender(base.Command):
    def __init__(self, bot: discord.ext.commands.Bot, allow_duplicated=False):
        logging.info("idolquiz init")
        super().__init__(bot, allow_duplicated)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_env = os.getenv("GOOGLE_CREDENTIALS")
        if creds_env is None:
            creds = Credentials.from_service_account_file(
                "credentials.json", scopes=scope
            )
        else:
            creds = Credentials.from_service_account_info(
                json.loads(creds_env), scopes=scope
            )
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1-V7uZEYEXVG87a_OT9y5QE3PTltOZin0HnnY3iaDJJw/edit?usp=sharing"
        self.workbook = client.open_by_url(url)

    @discord.app_commands.command(description="ランダムに取得します。")
    async def random(self, interaction: discord.Interaction):
        member_list = self.workbook.worksheets()[0].get_all_values()
        member_image_list = self.workbook.worksheets()[1].get_all_values()
        index = random.randint(0, len(member_image_list) - 1)
        member = next(
            filter(lambda x: x[0] == member_image_list[index][0], member_list), ""
        )
        embed = discord.Embed(
            title=member_image_list[index][0], description="{}期".format(member[1])
        )
        embed.set_image(url=member_image_list[index][1])
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(description="クイズができます。")
    async def quiz(self, interaction: discord.Interaction):
        windows = QuizWindows(workbook=self.workbook)
        await windows.run(interaction=interaction)

    @discord.app_commands.command(description="一覧が見れます")
    async def gallery(self, interaction: discord.Interaction):
        pages = GalleryPages(workbook=self.workbook)
        await pages.run(interaction=interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(IdolImageSender(bot=bot))
