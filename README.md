# bhoptimer-bot

A [discord.py](https://github.com/Rapptz/discord.py) bot for [shavit's bhoptimer](https://github.com/shavitush/bhoptimer/).

[Support Server](https://discord.gg/Sdc7tvD), PR's and issues are also welcome.

Includes:
 - Ability to download (from GameBanana or fastdl.me), extract, compress and send maps to FastDL (local or via FTP).

## Setup

Developed on Python 3.10.4:
 - Clone this repository.
 - Install requirements with `pip install -r requirements.txt`.
 - Edit `config.json`.
 - Run using `python bot.py` / `python3 bot.py`.

### `config.json` Fields Explained:
 - token - the Discord bot's token, found in the developer portal page for your application. If you are unsure on how to create a bot user, follow [this guide](https://discordpy.readthedocs.io/en/stable/discord.html).
 - prefix - the prefix used for bot commands.
 - maps_folder - the path to your server's maps folder, absolute path recommended, usually located in `cstrike/maps/`.
 - ftp_ip - the IP address to your FTP server for FastDL, leave blank if FastDL is local.
 - ftp_user - the username to your FTP server for FastDL, leave blank if FastDL is local.
 - ftp_pass - the password to your FTP server for FastDL, leave blank if FastDL is local.
 - fastdl_folder - the path to your server's maps folder on FastDL, absolute path recommended.
 - thumbnail - a link to an image that will serve as the 'thumbnail' for all embeds, can be left blank.

## Commands + Images

### downloadmap (aliases: dl/dm/dlmap/mapdl)
 - Allows the user to download maps onto the server, and uploads them to FastDL automatically.
 - Prefixless!
 - Supports fastdl.me (CASE SENSITIVE).
 
 ![image](https://github.com/flac/bhoptimer-bot/assets/53440695/d5e2cbd5-0fb9-4461-b419-ee747186184c)

 - And GameBanana.

 ![image](https://github.com/flac/bhoptimer-bot/assets/53440695/79051afb-acba-487c-bc57-b82bc9b380da)

## Credits
 - [Jeft](https://github.com/Jeftaei) and [lorp](https://github.com/ouwou) - Hopping on Visual Studio Code Multiplayer with me.
