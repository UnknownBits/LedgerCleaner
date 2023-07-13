import datetime, os, sqlite3
from .operation import SQLiteOperation
from mcdreforged.api.all import SimpleCommandBuilder

default_config = {
    "sqlite": "/server/world/ledger.sqlite",
    "reserve_days": 30
}

def on_load(server, prev_module):
    global sqlite
    config = server.load_config_simple('config.json', default_config)
    sqlite = SQLiteOperation(server, config["sqlite"], config["reserve_days"])
    builder = SimpleCommandBuilder()

    # declare your commands
    builder.command('!!ledger', sqlite.help)
    builder.command('!!ledger help', sqlite.help)
    builder.command('!!ledger size', sqlite.size)
    builder.command('!!ledger connect', sqlite.connect)
    builder.command('!!ledger close', sqlite.close)
    builder.command('!!ledger free', sqlite.free)
    builder.command('!!ledger clean', lambda: ...)
    builder.command('!!ledger clean confirm', sqlite.clean_confirm)

    # define your command nodes
    builder.arg('date', str)

    # done, now register the commands to the server
    builder.register(server)

def on_user_info(server, info):
    global sqlite
    command = info.content.split(" ")
    if info.content[:14] == "!!ledger clean":
        if len(command) == 2:
            sqlite.clean()
        elif not command[2] == "confirm":
            sqlite.clean(" ".join(command[2:]))

def on_unload(server):
    global sqlite
    if sqlite.connected:
        sqlite.close(commit=False, vacuum=False)

