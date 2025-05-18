import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import sys
import json
import os

TOKEN = 'YOUR_BOT_TOKEN' # Replace with your bot token
GUILD_ID = 12345678912345678 # Replace with your discord server ID

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
guild = discord.Object(id=GUILD_ID)

XP_FILE = 'xp.json'
MSG_FILE = 'messages.json'
xp_data = {}
message_data = {}

if os.path.exists(XP_FILE):
    try:
        with open(XP_FILE, 'r') as f:
            xp_data = json.load(f)
    except json.JSONDecodeError:
        print(f"{XP_FILE} is empty or corrupted, starting fresh.")
        xp_data = {}

def save_xp():
    with open(XP_FILE, 'w') as f:
        json.dump(xp_data, f, indent=4)

def save_messages():
    with open(MSG_FILE, 'w') as f:
        json.dump(message_data, f, indent=4)

@bot.event
async def on_message(message: discord.Message):
    if not message.author.bot:
        user_id = str(message.author.id)
        message_data[user_id] = message_data.get(user_id, 0) + 1
        save_messages()
    await bot.process_commands(message)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=guild)
    print(f"Logged in as {bot.user} and synced commands to guild {GUILD_ID}.")

@bot.tree.command(name="shutdown", description="Shutdown the bot", guild=guild)
@commands.is_owner()
async def shutdown(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Shutdown",
        description="Bot is shutting down... Goodbye! 👋",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)
    await bot.close()
    sys.exit()

@bot.tree.command(name="resetxp", description="Reset XP for a member", guild=guild)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="Member to reset XP for")
async def resetxp(interaction: discord.Interaction, member: discord.Member):
    user_id = str(member.id)
    if user_id in xp_data:
        xp_data[user_id] = 0
        save_xp()
        embed = discord.Embed(
            title="XP Reset",
            description=f"Reset XP for **{member.display_name}** to 0.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="XP Reset",
            description=f"User **{member.display_name}** has no XP recorded.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addxp", description="Add XP to a member", guild=guild)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="Member to add XP to", amount="Amount of XP to add")
async def addxp(interaction: discord.Interaction, member: discord.Member, amount: int):
    user_id = str(member.id)
    current_xp = xp_data.get(user_id, 0)
    xp_data[user_id] = current_xp + amount
    save_xp()

    embed = discord.Embed(
        title="XP Added",
        description=f"Added **{amount} XP** to **{member.display_name}**.",
        color=discord.Color.green()
    )
    embed.add_field(name="New Total XP", value=str(xp_data[user_id]))
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="getxp", description="Get XP of a member", guild=guild)
@app_commands.describe(member="Member to get XP of (optional)")
async def getxp(interaction: discord.Interaction, member: discord.Member):
    if member is None:
        member = interaction.user
    user_id = str(member.id)
    xp = xp_data.get(user_id, 0)

    embed = discord.Embed(
        title=f"{member.display_name}'s XP",
        description=f"Total XP: **{xp}**",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="resetcommands", description="Clear and resync all slash commands", guild=guild)
@commands.is_owner()
async def resetcommands(interaction: discord.Interaction):
    bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)

    embed = discord.Embed(
        title="Commands Reset",
        description="All slash commands have been cleared and resynced.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)
    print("Commands cleared and resynced.")

class LeaderboardView(View):
    def __init__(self, ctx, sorted_xp, page=0):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.sorted_xp = sorted_xp
        self.page = page
        self.max_page = (len(sorted_xp) - 1) // 10

        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page == self.max_page

    async def update_message(self, interaction: discord.Interaction):
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        start_idx = self.page * 10
        end_idx = start_idx + 10
        page_items = self.sorted_xp[start_idx:end_idx]

        description = ""
        rank = start_idx + 1

        for user_id, xp in page_items:
            user = self.ctx.guild.get_member(int(user_id))
            name = user.display_name if user else f"User ID {user_id}"
            description += f"**#{rank}** - {name}: **{xp} XP**\n"
            rank += 1

        embed = discord.Embed(
            title=f"🏆 XP Leaderboard (Page {self.page + 1}/{self.max_page + 1})",
            description=description if description else "No data available.",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Requested by {self.ctx.user.display_name}", icon_url=self.ctx.user.display_avatar.url)
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 0:
            self.page -= 1
            self.prev_button.disabled = self.page == 0
            self.next_button.disabled = False
            await self.update_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.max_page:
            self.page += 1
            self.next_button.disabled = self.page == self.max_page
            self.prev_button.disabled = False
            await self.update_message(interaction)

@bot.tree.command(name="leaderboard", description="Show XP leaderboard", guild=guild)
async def leaderboard(interaction: discord.Interaction):
    if not xp_data:
        embed = discord.Embed(
            title="XP Leaderboard",
            description="No XP data found yet.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return

    sorted_xp = sorted(xp_data.items(), key=lambda item: item[1], reverse=True)
    view = LeaderboardView(interaction, sorted_xp)
    embed = view.create_embed()

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="setxp", description="Set XP for a member", guild=guild)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member="Member to set XP for", amount="Amount of XP to set")
async def setxp(interaction: discord.Interaction, member: discord.Member, amount: int):
    user_id = str(member.id)
    previous_xp = xp_data.get(user_id, 0)
    xp_data[user_id] = amount
    save_xp()
    embed = discord.Embed(
        title="XP Set",
        description=f"Updated **{member.display_name}**'s XP from **{previous_xp}** to **{amount}**.",
        color=discord.Color.green()
    )
    embed.add_field(name="New Total XP", value=str(amount))
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

def format_date(dt) -> str:
    return dt.strftime('%B %d, %Y')

@bot.tree.command(name="profile", description="View a member's profile", guild=guild)
@app_commands.describe(member="The member to view (optional)")
async def profile(interaction: discord.Interaction, member: discord.Member):
    member = member or interaction.user
    user_id = str(member.id)
    xp = xp_data.get(user_id, 0)
    message_count = message_data.get(user_id, 0)
    join_date = format_date(member.joined_at)

    sorted_xp = sorted(xp_data.items(), key=lambda item: item[1], reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(sorted_xp) if uid == user_id), None)

    embed = discord.Embed(
        title=f"{member.display_name}'s Profile",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="✨ XP", value=f"{xp} XP", inline=False)
    embed.add_field(name="💬 Messages", value=f"{message_count} Messages", inline=False)
    embed.add_field(name="🗓️ Join Date", value=join_date, inline=False)
    embed.add_field(name="🏅 Rank", value=f"#{rank}" if rank else "Unranked", inline=False)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
