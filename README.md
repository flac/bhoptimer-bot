# bhoptimer-bot

A [discord.py](https://github.com/Rapptz/discord.py) bot for [shavit's bhoptimer](https://github.com/shavitush/bhoptimer/).
Includes:

 - Updating status message including playercount and current map (attempts to detect if server is offline).
 - Formatted list of online players, including hyperlinks to profiles.
 - RCON command execution, with console output.
 - Ability to check for a map within the mapcycle.
 - Ability to download (from GameBanana or Sojourner.me), extract, compress and send maps to FastDL (local or via FTP), including updating the mapcycle.

## Setup

Works with Python 3.7+:
 - Clone this repository.
 - Install requirements with `pip install -r requirements.txt`.
 - Edit `config.json`.
 - Run using `python bot.py` / `python3 bot.py`.

### `config.json` Fields Explained:
 - token - the Discord bot's token, found in the developer portal page for your application. If you are unsure on how to create a bot user, follow [this guide](https://discordpy.readthedocs.io/en/stable/discord.html).
 - prefix - the prefix used for bot commands.
 - server_ip - the bhop server's IP address.
 - server_port - the bhop server's port number.
 - rcon_password - the password used for RCON commands, if there isn't one for your server, add one to `server.cfg`, then edit this field.
 - mapcycle - the path to your server's mapcycle file, absolute path recommended, usually located in `cfg/mapcycle.txt`.
 - maps_folder - the path to your server's maps folder, absolute path recommended, usually located in `cstrike/maps/`.
 - ftp_ip - the IP address to your FTP server for FastDL, leave blank if FastDL is local.
 - ftp_user - the username to your FTP server for FastDL, leave blank if FastDL is local.
 - ftp_pass - the password to your FTP server for FastDL, leave blank if FastDL is local.
 - fastdl_folder - the path to your server's maps folder on FastDL, absolute path recommended.
 - admin_ids - a comma-separated array containing Discord ID's of users that will be allowed to execute RCON commands.
 - thumbnail - a link to an image that will serve as the 'thumbnail' for all embeds, can be left blank.
 - maps_channel - an ID of a Discord channel that will be used to send messages about newly added maps, can be left blank.

## Commands + Images

### players (aliases: online/playerlist)
 - Displays a list of online players, and bots.

 ![image](https://user-images.githubusercontent.com/53440695/147364515-3a04e7a1-2765-401a-8548-560b9a82603d.png)

 - Will also tell users if there is no one online.
 
 ![image](https://user-images.githubusercontent.com/53440695/147364398-62084280-877c-4e67-87f4-eb376d6ebf82.png)
 
### rcon
 - Allows execution of RCON commands, has 3 types of output:
 - No response (no command supplied).
 
 ![image](https://user-images.githubusercontent.com/53440695/147364809-05d582b4-09ed-4300-b192-77fc8b65b1b9.png)
 
 - Embedded response (standard).

 ![image](https://user-images.githubusercontent.com/53440695/147364834-9cbfc2e1-e22f-4222-847c-a50483927fe8.png)
 
 - File response (over 2000 characters).
 
 ![image](https://user-images.githubusercontent.com/53440695/147364998-96069614-bbf9-494e-8937-58959deb572a.png)

### checkmap (aliases: mapcycle/mapcheck)
 - Tells the user if a specific map is in the current mapcycle.
 - Prefixless! Allows the user to enter a mapname without the bhop_, kz_ or kz_bhop_.

 ![image](https://user-images.githubusercontent.com/53440695/147365118-1251302e-2233-4acd-9a0f-d447ef7c82a5.png)

 ![image](https://user-images.githubusercontent.com/53440695/147365126-bed3523a-ec7a-4482-abaa-8aa3a8d4a2ac.png)

 ![image](https://user-images.githubusercontent.com/53440695/147365140-13e25d13-f7cb-4862-a563-44342899d464.png)
 
 - Error message on non-existent map.
 
 ![image](https://user-images.githubusercontent.com/53440695/147365166-9e1e2839-d011-4461-99f8-314434e9e863.png)
 
### downloadmap (aliases: dl/dm/dlmap/mapdl)
 - Allows the user to download maps onto the server, and uploads them to FastDL automatically.
 - Prefixless!
 - Supports Sojourner.me (CASE SENSITIVE).
 
 ![image](https://user-images.githubusercontent.com/53440695/147365236-b2448165-0aaa-4caf-a2f1-625cec13608d.png)

 - And GameBanana.
 
 ![image](https://user-images.githubusercontent.com/53440695/147365430-b90cba0f-c60b-48db-b205-3dce802ad67e.png)
 
 - If the `maps_channel` field is included, a message will display in a separate channel informing users of new added maps.
 
 ![image](https://user-images.githubusercontent.com/53440695/147365486-86749cc5-4f5a-4051-bb97-3f0948c9e741.png)

#### In the event of the server being offline, the RCON and players commands will display an embed.
 - Downloading maps may still work if the FTP is online, or the FastDL is local.
 
 ![image](https://user-images.githubusercontent.com/53440695/147365531-829a134e-941b-4370-bbf2-f8708dbb92ab.png)

## Known Issues
 - The bot will not go back online if offline, it must be restarted when the server is back online.
 - bzip2 compression stage is not async.
 - In !players, bots have the time played, as well as their respective replay time.

## Credits
 - cherry - Showing me the initial idea of being able to remotely download maps to a server.
 - [lorp](https://github.com/ouwou) - Few fixes + constructive criticism of code.
 - [chris](https://github.com/5xp) - Fix for the RCON embed.
 - [Jeft](https://github.com/Jeftaei) - Fixes + general help with discord.py.
 - [Evan](https://github.com/EvanIMK) - [Open sourcing his bot](https://github.com/EvanIMK/BhopTimer-Discord-Bot) which served as the base initially.
 - kangaroo hoppers - Continuous usage of the bot, allowing me to find errors and add additional features.
 - zammyhop - Initial users of the bot.
