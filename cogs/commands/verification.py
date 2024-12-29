import discord
import aiosqlite
import yaml
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional

with open('config.yml', 'r') as file:
    data = yaml.safe_load(file)

guild_id = data["General"]["GUILD_ID"]
embed_color = data["General"]["EMBED_COLOR"]
button_emoji = data["Verification"]["EMOJI"]
button_label = data["Verification"]["LABEL"]
verified_role_id = data["Verification"]["VERIFIED_ROLE_ID"]
unverified_role_id = data["Verification"]["UNVERIFIED_ROLE_ID"]
staff_channel_id = data["Verification"]["STAFF_CHANNEL_ID"]
staff_role_id = data["Verification"]["STAFF_ROLE_ID"]
modal_title = data["Verification"]["Modal"]["TITLE"]
questions = data["Verification"]["Modal"]["QUESTIONS"]
accept_color = data["Approval"]["ACCEPT_COLOR"]
accept_emoji = data["Approval"]["ACCEPT_EMOJI"]
accept_label = data["Approval"]["ACCEPT_LABEL"]
deny_color = data["Approval"]["DENY_COLOR"]
deny_emoji = data["Approval"]["DENY_EMOJI"]
deny_label = data["Approval"]["DENY_LABEL"]

color_to_button_style = {
    "green": discord.ButtonStyle.green,
    "red": discord.ButtonStyle.red,
    "blurple": discord.ButtonStyle.blurple,
    "gray": discord.ButtonStyle.gray
}

class DenyModal(discord.ui.Modal, title='Deny Request'):
    def __init__(self):
        super().__init__(timeout=None)

    reason = discord.ui.TextInput(
        label="What is the reason?",
        placeholder='Type the reason here...',
        max_length=2000,
        style=discord.TextStyle.long,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        async with aiosqlite.connect('database.db') as db:
            try:
                cursor = await db.execute('SELECT * FROM verification WHERE message_id=?', (interaction.message.id,))
                request = await cursor.fetchone()

                reason = "\n\nReason: " + self.reason.value if self.reason.value else ""
                
                if request:
                    try:
                        member = interaction.guild.get_member(request[0])

                        embed = discord.Embed(title="Denied Verification Request", description=f"Your verification request has been denied!{reason}", color=discord.Color.red())
                        embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
                        embed.set_thumbnail(url=interaction.guild.icon.url)
                        embed.timestamp = datetime.now()
                        await member.send(embed=embed)
                    except:
                        pass
                    
                    await db.execute('DELETE FROM verification WHERE message_id=?', (interaction.message.id,))
                    await db.commit()
                
                view = ApproveButtons()
                view.accept.disabled = True
                view.deny.disabled = True

                embed = discord.Embed(title="[DENIED] Verification Request", description=f"Reason: {self.reason.value}", color=discord.Color.red())
                
                for field in interaction.message.embeds[0].fields:
                    embed.add_field(name=field.name, value=field.value, inline=False)

                embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
                embed.set_thumbnail(url=interaction.guild.icon.url)
                embed.timestamp = datetime.now()

                await interaction.message.edit(embed=embed, view=view)

                embed = discord.Embed(title="Verification", description=f"The user's verification request has been denied!{reason}", color=discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                try:
                    await interaction.response.send_message(f"An error occurred while processing your verification request.\n\nError: {e}", ephemeral=True)
                except:
                    await interaction.followup.send(f"An error occurred while processing your verification request.\n\nError: {e}")
                print(f"Deny Verification Error: {str(e)}")

class ApproveButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji=accept_emoji, label=accept_label, style=color_to_button_style.get(accept_color.lower(), discord.ButtonStyle.green), custom_id='approval:1')
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect('database.db') as db:
            guild = interaction.client.get_guild(guild_id)

            staff_role = guild.get_role(staff_role_id)

            verified_role = guild.get_role(verified_role_id)
            unverified_role = guild.get_role(unverified_role_id)

            if staff_role not in interaction.user.roles:
                embed = discord.Embed(title="Verification", description="You don't have permission to approve/deny verification requests!", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            cursor = await db.execute('SELECT * FROM verification WHERE message_id=?', (interaction.message.id,))
            request = await cursor.fetchone()
            
            if request:
                try:
                    member = guild.get_member(request[0])
                    await member.add_roles(verified_role)
                    await member.remove_roles(unverified_role)
                except:
                    pass
                
                await db.execute('DELETE FROM verification WHERE message_id=?', (interaction.message.id,))
                await db.commit()
            
            view = ApproveButtons()
            view.accept.disabled = True
            view.deny.disabled = True

            embed = discord.Embed(title="[ACCEPTED] Verification Request", color=discord.Color.green())

            for field in interaction.message.embeds[0].fields:
                embed.add_field(name=field.name, value=field.value, inline=False)

            embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.timestamp = datetime.now()

            view = ApproveButtons()
            view.accept.disabled = True
            view.deny.disabled = True

            await interaction.message.edit(embed=embed, view=view)

            embed = discord.Embed(title="Verification", description="The user has been verified!", color=discord.Color.green())
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji=deny_emoji, label=deny_label, style=color_to_button_style.get(deny_color.lower(), discord.ButtonStyle.red), custom_id='approval:2')
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
            guild = interaction.client.get_guild(guild_id)

            staff_role = guild.get_role(staff_role_id)

            if staff_role not in interaction.user.roles:
                embed = discord.Embed(title="Verification", description="You don't have permission to approve/deny verification requests!", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.send_modal(DenyModal())

class VerificationModal(discord.ui.Modal, title=modal_title):
    def __init__(self):
        super().__init__()

        self.requirements = {}
        self.requirement_descriptions = {}

        for i, question in enumerate(questions, 1):
            style = discord.TextStyle.long if question.get("STYLE", "").lower() == "long" else discord.TextStyle.short

            setattr(self, f'question{i}', discord.ui.TextInput(
                label=question["QUESTION"],
                placeholder=question["PLACEHOLDER"],
                style=style,
                required=question.get("REQUIRED", True),
                max_length=500,
            ))

            self.requirements[f'question{i}'] = question.get("REQUIREMENT", None)
            self.requirement_descriptions[f'question{i}'] = question.get("REQUIREMENT_DESCRIPTION", "Input does not meet the required criteria.")

            self.add_item(getattr(self, f'question{i}'))

    async def on_submit(self, interaction: discord.Interaction):
        async with aiosqlite.connect('database.db') as db:
            try:
                cursor = await db.execute('SELECT * FROM verification WHERE member_id=?', (interaction.user.id,))
                request = await cursor.fetchone()

                if request:
                    embed = discord.Embed(title="Verification", description="You've already submitted a verification request!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                for i in range(1, 6):
                    question_value = getattr(self, f'question{i}').value
                    requirement = self.requirements.get(f'question{i}')
                    requirement_description = self.requirement_descriptions.get(f'question{i}')

                    if requirement and requirement not in question_value:
                        embed = discord.Embed(title="Verification Error", description=requirement_description, color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return

                embed = discord.Embed(title="New Verification Request", color=discord.Color.from_str(embed_color))
                embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
                embed.set_thumbnail(url=interaction.guild.icon.url)
                embed.timestamp = datetime.now()

                for i in range(1, 6):
                    question_value = getattr(self, f'question{i}').value
                    question_label = getattr(self, f'question{i}').label
                    embed.add_field(
                        name=question_label,
                        value=question_value or "Not provided",
                        inline=False
                    )

                staff_channel = interaction.guild.get_channel(staff_channel_id)
                msg = await staff_channel.send(embed=embed, view=ApproveButtons())

                await db.execute('INSERT INTO verification VALUES (?,?)', (interaction.user.id, msg.id))
                await db.commit()

                embed = discord.Embed(title="Verification", description="Your verification request has been submitted and is pending review.", color=discord.Color.green())
                embed.timestamp = datetime.now()
                embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"An error occurred while processing your verification request.\n\nError: {e}", ephemeral=True)
                print(f"Verification Error: {str(e)}")

class VerificationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji=button_emoji, label=button_label, style=discord.ButtonStyle.green, custom_id='verification:1')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        verified_role = interaction.guild.get_role(verified_role_id)
        
        if verified_role in interaction.user.roles:
            embed = discord.Embed(title="Verification", description="You're already verified!", color=discord.Color.red())
            embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.timestamp = datetime.now()
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            await interaction.response.send_modal(VerificationModal())

class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_view(VerificationButton())
        self.bot.add_view(ApproveButtons())

    @app_commands.command(name="verification", description="Sends the verification panel!")
    async def verification(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel]) -> None:
        embed = discord.Embed(title="Verification", description="Click the button below to verify!", color=discord.Color.from_str(embed_color))
        embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=interaction.guild.name)

        channel = channel if channel else interaction.channel

        await channel.send(embed=embed, view=VerificationButton())

        await interaction.response.send_message("Sent!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot), guilds=[discord.Object(id=guild_id)])