import discord
import os

client = None


def set_client(bot_client):
    global client
    client = bot_client


async def join_vc_async(channel_id):
    channel = client.get_channel(int(channel_id))

    if not channel:
        return False

    await channel.connect()
    return True


async def leave_vc_async():
    for vc in client.voice_clients:
        await vc.disconnect()
    return True


async def play_sound_async(filename):
    if not client.voice_clients:
        return False

    vc = client.voice_clients[0]

    filepath = os.path.join(
        "sounds",
        filename
    )

    if vc.is_playing():
        vc.stop()

    source = discord.FFmpegPCMAudio(filepath)
    vc.play(source)
    return True


async def send_embed_async(
    channel_id,
    title,
    description,
    color=None,
    image_url=None,
    button_label=None,
    button_url=None
):
    channel = client.get_channel(
        int(channel_id)
    )

    if not channel:
        return False

    embed_color = 0x5865F2

    if color:
        color = color.replace("#", "")
        embed_color = int(color, 16)

    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )

    if image_url:
        embed.set_image(url=image_url)

    view = None

    if button_label and button_url:
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label=button_label,
                url=button_url
            )
        )

    await channel.send(
        embed=embed,
        view=view
    )
    return True


def get_status():
    if not client:
        return {
            "online": False,
            "guilds": 0,
            "voice_connected": False
        }

    return {
        "online": client.is_ready(),
        "guilds": len(client.guilds),
        "voice_connected": len(
            client.voice_clients
        ) > 0
    }