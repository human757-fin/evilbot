import json
import os

QUEUE_FILE = "bot_queue.json"


def push_command(data):
    commands = []

    if os.path.exists(QUEUE_FILE):
        with open(
            QUEUE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            try:
                commands = json.load(f)
            except:
                commands = []

    commands.append(data)

    with open(
        QUEUE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(commands, f, indent=4)


def join_vc(channel_id):
    push_command({
        "action": "join_vc",
        "channel_id": channel_id
    })


def leave_vc():
    push_command({
        "action": "leave_vc"
    })


def play_sound(filename):
    push_command({
        "action": "play_sound",
        "filename": filename
    })


def send_embed(
    channel_id,
    title,
    description,
    color=None,
    image_url=None,
    button_label=None,
    button_url=None
):
    push_command({
        "action": "send_embed",
        "channel_id": channel_id,
        "title": title,
        "description": description,
        "color": color,
        "image_url": image_url,
        "button_label": button_label,
        "button_url": button_url
    })


def get_status():
    status_file = "bot_status.json"

    if not os.path.exists(status_file):
        return {
            "online": False,
            "guilds": 0,
            "voice_connected": False
        }

    with open(
        status_file,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)