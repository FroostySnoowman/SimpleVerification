import discord
import yaml
from discord.ext import commands

with open('config.yml', 'r') as file:
    data = yaml.safe_load(file)

guild_id = data["General"]["GUILD_ID"]
embed_color = data["General"]["EMBED_COLOR"]
unverified_role_id = data["Verification"]["UNVERIFIED_ROLE_ID"]

class MemberEventsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        
        try:
            guild = self.bot.get_guild(guild_id)
            unverified_role = guild.get_role(unverified_role_id)
            await member.add_roles(unverified_role)
        except Exception as e:
            print(f"An error occurred while adding the unverified role to {member.display_name}: {e}")

async def setup(bot):
    await bot.add_cog(MemberEventsCog(bot))