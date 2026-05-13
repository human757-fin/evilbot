import discord
from discord import app_commands
import json
import os
from datetime import timedelta
from dotenv import load_dotenv
import asyncio
import feedparser

from config import (
    SPAM_LIMIT,
    SPAM_SECONDS,
    MAX_MENTIONS,
    TIMEOUT_MINUTES,
    DEFAULT_WELCOME_COLOR,
    BANNED_WORDS
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")
TIKTOK_CHANNEL_ID = int(os.getenv("TIKTOK_CHANNEL_ID"))
UPLOAD_PING_ROLE_ID = int(os.getenv("UPLOAD_PING_ROLE_ID"))

LAST_VIDEO_FILE = "last_tiktok.txt"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

guild = discord.Object(id=GUILD_ID)

SETTINGS_FILE = "settings.json"
MESSAGE_CACHE = {}


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_last_video():
    if os.path.exists(LAST_VIDEO_FILE):
        with open(LAST_VIDEO_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def save_last_video(video_url):
    with open(LAST_VIDEO_FILE, "w", encoding="utf-8") as f:
        f.write(video_url)

def write_channels():
    channels = []

    for guild in client.guilds:
        for channel in guild.text_channels:
            channels.append({
                "id": channel.id,
                "name": f"#{channel.name}"
            })

        for channel in guild.voice_channels:
            channels.append({
                "id": channel.id,
                "name": f"🔊 {channel.name}"
            })

    with open(
        "channels.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(channels, f, indent=4)

async def process_queue():
    queue_file = "bot_queue.json"

    if not os.path.exists(queue_file):
        return

    with open(
        queue_file,
        "r",
        encoding="utf-8"
    ) as f:
        try:
            commands = json.load(f)
        except:
            commands = []

    open(queue_file, "w").write("[]")

    for cmd in commands:
        action = cmd.get("action")

        if action == "join_vc":
            channel = client.get_channel(
                int(cmd["channel_id"])
            )

            if channel:
                await channel.connect()

        elif action == "leave_vc":
            for vc in client.voice_clients:
                await vc.disconnect()

        elif action == "play_sound":
            if client.voice_clients:
                vc = client.voice_clients[0]

                filepath = os.path.join(
                    "sounds",
                    cmd["filename"]
                )

                if vc.is_playing():
                    vc.stop()

                vc.play(
                    discord.FFmpegPCMAudio(
                        filepath
                    )
                )

        elif action == "stop_sound":
            if client.voice_clients:
                vc = client.voice_clients[0]

                if vc.is_playing():
                    vc.stop()

        elif action == "send_embed":
            channel = client.get_channel(
                int(cmd["channel_id"])
            )

            if not channel:
                continue

            color = 0x5865F2

            if cmd.get("color"):
                color = int(
                    cmd["color"].replace("#", ""),
                    16
                )

            embed = discord.Embed(
                title=cmd["title"],
                description=cmd[
                    "description"
                ],
                color=color
            )

            if cmd.get("image_url"):
                embed.set_image(
                    url=cmd["image_url"]
                )

            view = None

            if (
                cmd.get("button_label")
                and cmd.get("button_url")
            ):
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label=cmd[
                            "button_label"
                        ],
                        url=cmd[
                            "button_url"
                        ]
                    )
                )

            await channel.send(
                embed=embed,
                view=view
            )

async def check_tiktok_uploads():
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            url = f"https://rsshub.app/tiktok/user/{TIKTOK_USERNAME}"
            feed = feedparser.parse(url)

            if feed.entries:
                latest = feed.entries[0]
                video_url = latest.link

                last_video = load_last_video()

                # First run: save without posting
                if last_video is None:
                    save_last_video(video_url)

                elif video_url != last_video:
                    save_last_video(video_url)

                    channel = client.get_channel(UPLOAD_CHANNEL_ID)

                    if channel:
                        role_ping = f"<@&{UPLOAD_ROLE_ID}>"

                        embed = discord.Embed(
                            title="New TikTok Upload",
                            description=f"{role_ping}\n{video_url}",
                            color=0xFE2C55
                        )

                        await channel.send(embed=embed)

        except Exception as e:
            print("TikTok watcher error:", e)

        await asyncio.sleep(300)

def write_status():
    voice_channel = None

    if client.voice_clients:
        vc = client.voice_clients[0]
        if vc.channel:
            voice_channel = vc.channel.name

    with open(
        "bot_status.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump({
            "online": client.is_ready(),
            "guilds": len(client.guilds),
            "voice_connected":
                len(client.voice_clients) > 0,
            "voice_channel": voice_channel
        }, f)

async def background_loop():
    await client.wait_until_ready()

    while not client.is_closed():
        await process_queue()
        write_status()
        write_channels()
        await discord.utils.sleep_until(
            discord.utils.utcnow()
            + timedelta(seconds=2)
        )

class LinkButtons(discord.ui.View):
    def __init__(self, buttons):
        super().__init__()

        for label, url in buttons:
            if label and url:
                self.add_item(
                    discord.ui.Button(label=label, url=url)
                )


def is_staff(member):
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
    )


def excessive_caps(text):
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 8:
        return False

    caps = sum(1 for c in letters if c.isupper())
    return caps / len(letters) > 0.7


async def punish(member, reason, source_channel):
    try:
        await member.timeout(
            timedelta(minutes=TIMEOUT_MINUTES),
            reason=reason
        )

        log_channel = client.get_channel(LOG_CHANNEL_ID)

        embed = discord.Embed(
            title="🔨 Auto Moderation Action",
            color=0xED4245
        )
        embed.add_field(
            name="User",
            value=f"{member} ({member.id})",
            inline=False
        )
        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        if log_channel:
            await log_channel.send(embed=embed)

    except discord.Forbidden:
        pass


@client.event
async def on_ready():
    synced = await tree.sync(guild=guild)
    print(f"Synced {len(synced)} commands")
    print(f"Logged in as {client.user}")
    write_status()
    write_channels()
    client.loop.create_task(
        background_loop()
    )
    client.loop.create_task(
        check_tiktok_uploads()
    )


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("$ping"):
        await message.channel.send("Pong")
    
    if message.content.startswith("$rules"):
        parts = message.content.split()

        if len(parts) < 2:
            await message.channel.send(
                "Usage: $rules <channel_id>"
            )
            return

        try:
            channel_id = int(parts[1])
        except ValueError:
            await message.channel.send(
                "Channel ID must be numeric."
            )
            return

        channel = client.get_channel(channel_id)

        if not channel:
            await message.channel.send(
                "Couldn't find that channel."
            )
            return

        embed = discord.Embed(
            title="📜 Server Rules",
            description="""
**1. No Spamming**
No message flooding, repeated messages, excessive emojis, copypastes or unnecessary pings.

**2. No Racism, Discrimination, or Hate Speech**
Any form of racism, sexism or discrimination is strictly prohibited.

**3. Swearing Is Allowed — Know Your Limits**
Casual swearing is fine, but don’t go overboard or use it to attack others.

**4. No Harassment**
No bullying, threats, or personal attacks. Keep it cool.

**5. Respect Everyone**
Treat all members and staff with respect. Disagreements are fine — disrespect is not.
No Drama or Public Arguments

**6. Listen to Staff**
Moderators have the final say. Arguing with staff decisions publicly may result in punishment.

**7. Use Common Sense**
If something feels like it might break the rules, it probably does.
    """.strip(),
            color=0xFF0000
        )

        await channel.send(embed=embed)
        await message.channel.send(
            f"Rules posted in {channel.mention} ✅"
        )

    if message.content.startswith("$joinvc"):
        if not message.author.guild_permissions.administrator:
            await message.channel.send(
                "Admin only command."
            )
            return

        parts = message.content.split()

        if len(parts) < 2:
            await message.channel.send(
                "Usage: $joinvc <voice_channel_id>"
            )
            return

        try:
            channel_id = int(parts[1])
        except ValueError:
            await message.channel.send(
                "Voice channel ID must be numeric."
            )
            return

        channel = client.get_channel(channel_id)

        if not channel:
            await message.channel.send(
                "Couldn't find that voice channel."
            )
            return

        if not isinstance(channel, discord.VoiceChannel):
            await message.channel.send(
                "That ID is not a voice channel."
            )
            return

        try:
            if message.guild.voice_client:
                await message.guild.voice_client.move_to(channel)
                await message.channel.send(
                    f"Moved to **{channel.name}** ✅"
                )
            else:
                await channel.connect()
                await message.channel.send(
                    f"Joined **{channel.name}** ✅"
                )

        except discord.ClientException:
            await message.channel.send(
                "Failed to connect to voice channel."
            )
    if message.content.startswith("$leavevc"):
        if not message.author.guild_permissions.administrator:
            return

        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.channel.send("Disconnected ✅")

    if message.content.startswith("$play"):
        if not message.author.guild_permissions.administrator:
            await message.channel.send(
                "Admin only command."
            )
            return

        parts = message.content.split(maxsplit=1)

        if len(parts) < 2:
            await message.channel.send(
                "Usage: $play <filename>"
            )
            return

        filename = parts[1]
        filepath = f"/home/container/bot/sounds/{filename}"

        if not os.path.isfile(filepath):
            await message.channel.send(
                f"File not found: {filename}"
            )
            return

        vc = message.guild.voice_client

        if not vc:
            await message.channel.send(
                "Bot is not in a voice channel."
            )
            return

        if vc.is_playing():
            vc.stop()

        source = discord.FFmpegPCMAudio(filepath)
        vc.play(source)

        await message.channel.send(
            f"Playing **{filename}** ▶️"
        )

    if is_staff(message.author):
        return

    content_lower = message.content.lower()
    user_id = message.author.id

    if user_id not in MESSAGE_CACHE:
        MESSAGE_CACHE[user_id] = []

    MESSAGE_CACHE[user_id].append(message.created_at)

    recent = [
        t for t in MESSAGE_CACHE[user_id]
        if (message.created_at - t).seconds <= SPAM_SECONDS
    ]
    MESSAGE_CACHE[user_id] = recent

    if len(recent) >= SPAM_LIMIT:
        await punish(message.author, "Spam detected", message.channel)
        return

    if len(message.mentions) > MAX_MENTIONS:
        await punish(
            message.author,
            "Excessive mentions",
            message.channel
        )
        return

    if excessive_caps(message.content):
        await punish(
            message.author,
            "Excessive caps",
            message.channel
        )
        return

    for word in BANNED_WORDS:
        if word in content_lower:
            await punish(
                message.author,
                f"Blocked content: {word}",
                message.channel
            )
            return


@client.event
async def on_member_join(member):
    settings = load_settings()
    guild_id = str(member.guild.id)

    if guild_id not in settings:
        return

    guild_settings = settings[guild_id]

    role_id = guild_settings.get("default_role")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                print("Role hierarchy issue.")

    channel_id = guild_settings.get("welcome_channel")
    welcome_text = guild_settings.get("welcome_message")
    img_url = guild_settings.get("img_url")
    color = guild_settings.get(
        "color",
        DEFAULT_WELCOME_COLOR
    )

    try:
        color = color.replace("#", "")
        embed_color = int(color, 16)
    except ValueError:
        embed_color = 0x57F287

    if channel_id and welcome_text:
        channel = member.guild.get_channel(channel_id)

        if channel:
            embed = discord.Embed(
                title="Welcome!",
                description=welcome_text.format(
                    user=member.mention,
                    server=member.guild.name
                ),
                color=embed_color
            )

            if img_url:
                embed.set_image(url=img_url)

            await channel.send(embed=embed)


@tree.command(name="test", description="Test", guild=guild)
async def slash_test(interaction: discord.Interaction):
    await interaction.response.send_message("Working ✅")


@tree.command(name="setwelcome", description="Set welcome", guild=guild)
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    welcome_text: str,
    img_url: str = None,
    color: str = DEFAULT_WELCOME_COLOR
):
    settings = load_settings()
    guild_id = str(interaction.guild.id)

    settings[guild_id] = {
        "welcome_channel": channel.id,
        "default_role": role.id,
        "welcome_message": welcome_text,
        "img_url": img_url,
        "color": color
    }

    save_settings(settings)

    await interaction.response.send_message(
        "Welcome settings saved ✅",
        ephemeral=True
    )


client.run(BOT_TOKEN)