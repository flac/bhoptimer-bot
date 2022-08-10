import aiofiles
import aioftp
import aiohttp
import bz2
import discord
import json
import os
import patoolib
import re
import requests
import shutil
import valve.rcon
import valve.source.a2s as a2s
from datetime import datetime, timedelta
from discord.errors import HTTPException
from discord.ext import commands, tasks
from hurry.filesize import size

with open("config.json", "r") as config:
    cfg = json.load(config)

# bot related
TOKEN = cfg["token"]
PREFIX = cfg["prefix"]

# server related
IP = cfg["server_ip"]
PORT = int(cfg["server_port"])
RCON_PW = cfg["rcon_password"]
MAPCYCLE = cfg["mapcycle"]
MAPS_FOLDER = cfg["maps_folder"]

# fastdl related
FTP_IP = cfg["ftp_ip"]
FTP_USER = cfg["ftp_user"]
FTP_PASS = cfg["ftp_pass"]
FASTDL_FOLDER = cfg["fastdl_folder"]

# discord related
ADMIN_IDS = cfg["admin_ids"]
THUMBNAIL = cfg["thumbnail"]
MAPS_CHANNEL = int(cfg["maps_channel"])

bot = commands.Bot(command_prefix=PREFIX)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
}

maptypes = ["", "bhop_", "kz_", "kz_bhop_"]
valve.rcon.RCONMessage.ENCODING = "utf-8"


@bot.event
async def on_ready():
    status.start()


# "static" server variable, define here so some commands can run without server being online
with a2s.ServerQuerier((IP, PORT)) as server:
    try:
        server_name = "{server_name}".format(**server.info())
        server_offline = False
    except a2s.NoResponseError:
        server_offline = True
        server_name = "Server Offline"


# presence changer
@tasks.loop(seconds=120.0)
async def status():
    with a2s.ServerQuerier((IP, PORT)) as server:
        if server_offline:
            await bot.change_presence(activity=discord.Game("Server Offline."))
        else:
            await bot.change_presence(activity=discord.Game("{map} ({player_count}/{max_players})".format(**server.info())))


# online player list
@bot.command(aliases=["online", "playerlist"], brief="Shows a list of online players")
# @commands.cooldown(1, 5, commands.BucketType.guild)
async def players(ctx):
    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{server_name}")
    embed.color = 0x1

    if not server_offline:

        with a2s.ServerQuerier((IP, PORT)) as server:

            embed.set_author(name="{map} - {player_count}/{max_players} players online".format(**server.info()))

            status = valve.rcon.execute((IP, PORT), RCON_PW, "status")
            rcon_players = status.split("\n", 9)[9].split("\n")
            final_list = ""

            for player in rcon_players:
                try:
                    name = re.findall(r'"([^"]*)"', player)[0]

                    # fixed the dumb method of finding bots thanks lorp
                    if re.search(r"BOT\s+active$", player):
                        bot = True
                    else:
                        id = re.findall(r"\[.*?]", player)[0]
                        bot = False

                    # prevent bot from having profile url
                    valve_players = server.players()
                    for valve_player in valve_players["players"]:
                        if bot:
                            final_list += f"{name} - " + str(
                                timedelta(seconds=int("{duration:.0f}".format(**valve_player), base=10))) + "\n"
                            break
                        else:
                            if name == valve_player["name"]:
                                final_list += f"[ {name} ](https://steamcommunity.com/profiles/{id}) - " + str(timedelta(seconds=int("{duration:.0f}".format(**valve_player), base=10))) + "\n"
                                break

                except IndexError:
                    pass

            if final_list == "":
                embed.add_field(name="Players:", value="There are no active players on the server.", inline=False)
            else:
                embed.add_field(name="Players:", value=final_list, inline=False)
            embed.add_field(name="Join Server:", value=f"steam://connect/{IP}:{PORT}", inline=False)
            await ctx.send(embed=embed)

    else:
        embed.color = 0xd2222d
        embed.add_field(name="Server Offline.", value="Server is currently offline.")
        await ctx.send(embed=embed)


# rcon executor
@bot.command(brief="Execute RCON commands from Discord", usage="[command]")
# @commands.cooldown(1, 5, commands.BucketType.guild)
async def rcon(ctx, *args):
    user = ctx.message.author

    if not server_offline:

        if str(user.id) in ADMIN_IDS:
            with a2s.ServerQuerier((IP, PORT)) as server:

                command = valve.rcon.execute((IP, PORT), RCON_PW, " ".join(args[:]))

                embed = discord.Embed(colour=discord.Colour(0xcc9900), timestamp=datetime.utcnow(), description=f"```{command}```")
                embed.set_author(name="RCON")
                embed.set_footer(text=f"{server_name}")

                # send response as txt if over discord 2k chars limit (thanks chris)
                try:
                    if command == "":
                        await ctx.send("```No response.```")
                    else:
                        await ctx.send(embed=embed)

                except HTTPException:
                    with open("response.txt", "w") as resp:
                        resp.write(command)
                    await ctx.send("Response over 2000 characters.", file=discord.File(r"response.txt"))

        else:
            await ctx.send("UID not in Admin ID whitelist.")

    else:
        embed = discord.Embed(timestamp=datetime.utcnow())
        embed.set_author(name="RCON")
        embed.color = 0xd2222d
        embed.add_field(name="Server Offline.", value="Server is currently offline.")
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=f"{server_name}")
        await ctx.send(embed=embed)


# mapcycle checker
@bot.command(aliases=["mapcycle", "mapcheck"], brief="Check if specified map is in the mapcycle", usage="[map]")
# @commands.cooldown(1, 5, commands.BucketType.guild)
async def checkmap(ctx, arg):
    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_author(name="Mapcycle")
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{server_name}")

    with open(MAPCYCLE, "r") as mc:
        for line in mc.readlines():
            for maptype in maptypes:
                if line.rstrip() == f"{maptype}{arg}":
                    embed.color = 0x238823
                    embed.description = f"``{maptype}{arg}`` was found in the mapcycle."
                    return await ctx.send(embed=embed)

        embed.color = 0xd2222d
        embed.description = f"``{arg}`` was **not** found in the mapcycle."
        return await ctx.send(embed=embed)


# download map function
@bot.command(aliases=["dl", "dm", "dlmap" "mapdl"], brief="Download a map using a GameBanana link, or map name.")
# @commands.cooldown(1, 5, commands.BucketType.guild)
async def downloadmap(ctx, arg):
    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{server_name}")
    embed.colour = 0x35cbdb

    mapname = str(arg)
    maps_channel = bot.get_channel(MAPS_CHANNEL)

    # gamebanana method
    if mapname.startswith("https://gamebanana.com/mods/"):
        embed.set_author(name="Map Downloader - GameBanana")
        item_id = mapname.split("/")[4]

        # gb api stuff
        gb_api_req = requests.get(f"https://api.gamebanana.com/Core/Item/Data?itemtype=Mod&itemid={item_id}&fields=name,Files().aFiles()").json()

        gb_name = gb_api_req[0]
        mod_id = list(gb_api_req[1])[0]
        mapfile_name = gb_api_req[1].get(mod_id).get("_sFile")
        mapfile_size = gb_api_req[1].get(mod_id).get("_nFilesize")
        download_url = gb_api_req[1].get(mod_id).get("_sDownloadUrl")

        gb_filelist_req = requests.get(f"https://gamebanana.com/apiv9/File/{mod_id}").json()
        folder_name = list(gb_filelist_req.get("_aMetadata").get("_aArchiveFileTree"))[0]

        # attempt to get files within folder if applicable
        try:
            map_files = gb_filelist_req.get("_aMetadata").get("_aArchiveFileTree").get(folder_name)
        except AttributeError:
            map_files = gb_filelist_req.get("_aMetadata").get("_aArchiveFileTree")
            folder_name = ""

        embed.description = f"Downloading **{gb_name}** from GameBanana, {size(mapfile_size)}..."
        msg = await ctx.send(embed=embed)

        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as resp:

                map_file = await aiofiles.open(f"{MAPS_FOLDER}/{mapfile_name}", mode="wb")
                await map_file.write(await resp.read())
                await map_file.close()

                embed.add_field(name="Contents:", value=map_files)
                embed.description = f"Extracting **{mapfile_name}**..."
                await msg.edit(embed=embed)

                patoolib.extract_archive(f"{MAPS_FOLDER}/{mapfile_name}", outdir=f"{MAPS_FOLDER}", interactive=False)

                # move files out of any folders to main maps folder
                for file in map_files:
                    shutil.move(f"{MAPS_FOLDER}/{folder_name}/{file}", f"{MAPS_FOLDER}/{file}")

                embed.description = f"Compressing contents..."
                await msg.edit(embed=embed)

                compressed_files = []

                # only want bsps, navs are small enough to be downloaded uncompressed
                for file in map_files:
                    if str(file).endswith('.bsp'):
                        with bz2.open(f"{MAPS_FOLDER}/{file}.bz2", "wb") as compressed_file:
                            with open(f"{MAPS_FOLDER}/{file}", "rb") as bsp:
                                data = bsp.read()
                                compressed_file.write(data)
                                compressed_files.append(f"{file}.bz2")
                    else:
                        pass

                embed.description = f"Moving files to FastDL..."
                embed.remove_field(0)
                await msg.edit(embed=embed)

                for file in compressed_files:

                    if FTP_IP:
                        async with aioftp.Client.context(FTP_IP, user=FTP_USER, password=FTP_PASS) as ftp:
                            await ftp.upload(f"{MAPS_FOLDER}/{file}", f"{FASTDL_FOLDER}/{file}", write_into=True)

                        # cleanup
                        try:
                            os.remove(f"{MAPS_FOLDER}/{file}")
                            os.remove(f"{MAPS_FOLDER}/{mapfile_name}")
                        # extracting zips with folders in them deletes the zip
                        except FileNotFoundError:
                            pass

                        # delete folders if zip has one in it
                        if folder_name:
                            try:
                                os.removedirs(f"{MAPS_FOLDER}/{folder_name}")
                            except FileNotFoundError:
                                pass

                    else:
                        try:
                            # have to specify full path to overwrite existing
                            shutil.move(f"{MAPS_FOLDER}/{file}", f"{FASTDL_FOLDER}/{file}")

                            # cleanup
                            os.remove(f"{MAPS_FOLDER}/{mapfile_name}")

                            # delete folders if zip has one in it
                            if folder_name:
                                try:
                                    os.removedirs(f"{MAPS_FOLDER}/{folder_name}")
                                except FileNotFoundError:
                                    pass

                        # weird error even though all maps get moved in a mappack
                        except FileNotFoundError:
                            pass

                # update mapcycle
                file_list = os.listdir(MAPS_FOLDER)
                with open(MAPCYCLE, "w") as mapcycle_file:
                    for file in file_list:
                        if str(file).endswith(".bsp"):
                            mapcycle_file.write(file[:-4] + "\n")

                embed.description = f"Successfully added **{gb_name}**."
                await msg.edit(embed=embed)

                if MAPS_CHANNEL:
                    await maps_channel.send(f"```Added {gb_name}.```\n{mapname}")

                else:
                    pass

    # acer/sojourner method
    else:
        download_url = "http://sojourner.me/fastdl/maps/"
        sojourner_file = mapname + ".bsp.bz2"
        map_not_found = 0

        # check for bhop_ / kz_ / kz_bhop_
        for maptype in maptypes:

            if requests.head(f"{download_url}{maptype}{sojourner_file}", headers=headers).status_code == 200:
                embed.set_author(name="Map Downloader - Sojourner")
                embed.description = f"Downloading **{maptype}{sojourner_file}** from Sojourner.me..."
                msg = await ctx.send(embed=embed)

                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{download_url}{maptype}{sojourner_file}") as resp:

                        map_file = await aiofiles.open(f"{MAPS_FOLDER}/{maptype}{sojourner_file}", mode="wb")
                        await map_file.write(await resp.read())
                        await map_file.close()

                        embed.description = f"Extracting **{maptype}{sojourner_file}**..."
                        await msg.edit(embed=embed)

                        patoolib.extract_archive(f"{MAPS_FOLDER}/{maptype}{sojourner_file}", outdir=f"{MAPS_FOLDER}", interactive=False)

                        embed.description = f"Moving **{maptype}{sojourner_file}** to FastDL..."
                        await msg.edit(embed=embed)

                        if FTP_IP:
                            async with aioftp.Client.context(FTP_IP, user=FTP_USER, password=FTP_PASS) as ftp:
                                await ftp.upload(f"{MAPS_FOLDER}/{maptype}{sojourner_file}", f"{FASTDL_FOLDER}/{maptype}{sojourner_file}", write_into=True)

                            # cleanup
                            os.remove(f"{MAPS_FOLDER}/{maptype}{sojourner_file}")

                        else:
                            # have to specify full path to overwrite existing
                            shutil.move(f"{MAPS_FOLDER}/{maptype}{sojourner_file}", f"{FASTDL_FOLDER}/{maptype}{sojourner_file}")

                        # update mapcycle
                        file_list = os.listdir(MAPS_FOLDER)
                        with open(MAPCYCLE, "w") as mapcycle_file:
                            for file in file_list:
                                if str(file).endswith(".bsp"):
                                    mapcycle_file.write(file[:-4] + "\n")

                        embed.description = f"Successfully added **{maptype}{mapname}**."
                        await msg.edit(embed=embed)

                        if MAPS_CHANNEL:
                            await maps_channel.send(
                                f"```Added {maptype}{mapname}.```\n{download_url}{maptype}{sojourner_file}")
                            break

                        else:
                            break
            else:
                map_not_found += 1
                if map_not_found == 4:
                    embed.set_author(name="Map Downloader - Sojourner")
                    embed.description = f"Unable to find map on Sojourner.me."
                    embed.color = 0xd2222d
                    await ctx.send(embed=embed)


# cooldowns, remove the """s and the #s from the lines with @commands.cooldown to enable
"""
@players.error
async def players_cooldown(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = "This command is on cooldown, please try again in {:.2f}s.".format(error.retry_after)
        await ctx.send(msg)

@rcon.error
async def rcon_cooldown(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = "This command is on cooldown, please try again in {:.2f}s.".format(error.retry_after)
        await ctx.send(msg)

@checkmap.error
async def checkmap_cooldown(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = "This command is on cooldown, please try again in {:.2f}s.".format(error.retry_after)
        await ctx.send(msg)

@downloadmap.error
async def downloadmap_cooldown(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = "This command is on cooldown, please try again in {:.2f}s.".format(error.retry_after)
        await ctx.send(msg)        
"""

bot.run(TOKEN)
