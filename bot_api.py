BOT_STATUS = {
    "online": True,
    "guilds": 1,
    "voice_connected": False
}


def get_status():
    return BOT_STATUS


def join_vc(channel_id):
    print("join vc", channel_id)
    BOT_STATUS["voice_connected"] = True


def leave_vc():
    print("leave vc")
    BOT_STATUS["voice_connected"] = False


def play_sound(filename):
    print("play", filename)


def send_embed(
    channel_id,
    title,
    description,
    color=None,
    image_url=None,
    button_label=None,
    button_url=None
):
    print(
        title,
        description,
        color,
        image_url,
        button_label,
        button_url
    )