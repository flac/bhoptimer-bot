import discord
from discord.errors import HTTPException
from discord.ext import commands, tasks
from requests.models import HTTPError
import valve.source.a2s as a2s
import valve.rcon
import json
from datetime import datetime, timedelta
import re
import mysql.connector
import requests
import aiohttp
import aiofiles
from hurry.filesize import size
import patoolib

with open("config.json", "r") as config:
    cfg = json.load(config)

#bot related
TOKEN = cfg["token"]
API_KEY = cfg["sj_api_key"]
PREFIX = cfg["prefix"]

#server related
IP = cfg["server_ip"]
PORT = int(cfg["server_port"])
RCON_PW = cfg["rcon_password"]
MAPCYCLE = cfg["mapcycle"]
STYLES_CFG = cfg["styles_config"]
MAPS_FOLDER = cfg["maps_folder"]

#database related
DB_IP = cfg["db_ip"]
DB_USER = cfg["db_user"]
DB_PASS = cfg["db_pass"]
DB_DB = cfg["db_database"]

#discord related
ADMIN_IDS = cfg["admin_ids"]
THUMBNAIL = cfg["thumbnail"]

bot = commands.Bot(command_prefix=PREFIX)

db = {
  "user": DB_USER,
  "password": DB_PASS,
  "host": DB_IP,
  "database": DB_DB
}

maptypes = ["", "bhop_", "kz_", "kz_bhop_"]

@bot.event
async def on_ready():
    status.start()

#"static" server variable, define here so some commands can run without server being online
with a2s.ServerQuerier((IP, PORT)) as server:
    try:
       server_name = "{server_name}".format(**server.info())
       serverOffline = False
    except a2s.NoResponseError:
        serverOffline = True
        server_name = "Server Offline"

#embed template
embed = discord.Embed(timestamp=datetime.utcnow())
embed.set_thumbnail(url=THUMBNAIL)
embed.set_footer(text=f"{server_name}")     


#presence changer
@tasks.loop(seconds=120.0)
async def status():
    with a2s.ServerQuerier((IP, PORT)) as server:
        if serverOffline:
            await bot.change_presence(activity=discord.Game("Server Offline."))
        else:
            await bot.change_presence(activity=discord.Game("{map} ({player_count}/{max_players})".format(**server.info())))

#online player list
@bot.command(aliases=["online", "playerlist"], brief="Shows a list of online players")
#@commands.cooldown(1, 5, commands.BucketType.guild)
async def players(ctx):

    embed.color = 0x1

    if not serverOffline:

        with a2s.ServerQuerier((IP, PORT)) as server:
                
            embed.set_author(name="{map} - {player_count}/{max_players} players online".format(**server.info()))
            
            status = valve.rcon.execute((IP, PORT), RCON_PW, "status")
            rconPlayers = status.split("\n",9)[9].split("\n")
            finalList = ""

            for player in rconPlayers:
                try:
                    name = re.findall(r'"([^"]*)"', player)[0]

                    #really dumb way to separate bot from player but works i guess
                    if "BOT                                     active" in player:
                        bot = True
                    else:
                        id = re.findall(r"\[.*?]", player)[0]
                        bot = False

                    #prevent bot from having profile url
                    valvePlayers = server.players()
                    for valvePlayer in valvePlayers["players"]:
                        if bot == True:
                            finalList += f"{name} - " + str(timedelta(seconds=int(("{duration:.0f}").format(**valvePlayer), base=10))) + "\n"
                            break
                        else:
                            if name == valvePlayer["name"]:
                                finalList += f"[ {name} ](https://steamcommunity.com/profiles/{id}) - " + str(timedelta(seconds=int(("{duration:.0f}").format(**valvePlayer), base=10))) + "\n"
                                break
                            
                except IndexError:
                    pass

            embed.add_field(name="Players:", value=finalList)
            embed.add_field(name="Join Server:", value=f"steam://connect/{IP}:{PORT}")
            await ctx.send(embed=embed)
    
    else:
        embed.color = 0xd2222d
        embed.add_field(name="Server Offline.", value="Server is currently offline.")
        await ctx.send(embed=embed)

#rcon executor
@bot.command(brief="Execute RCON commands from Discord", usage="[command]")
#@commands.cooldown(1, 5, commands.BucketType.guild)
async def rcon(ctx, *args):
    user = ctx.message.author
    if str(user.id) in ADMIN_IDS:
        with a2s.ServerQuerier((IP, PORT)) as server:
            command = valve.rcon.execute((IP, PORT), RCON_PW, " ".join(args[:]))
            embed = discord.Embed(colour=discord.Colour(0xcc9900), timestamp=datetime.utcnow(), description=f"```{command}```")
            embed.set_author(name="RCON")
            embed.set_thumbnail(url=THUMBNAIL)
            embed.set_footer(text="{server_name}".format(**server.info()))

            #send response as txt if over discord 2k chars limit
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

#mapcycle checker
@bot.command(aliases=["mapcycle", "mapcheck"], brief="Check if specified map is in the mapcycle", usage="[map]")
#@commands.cooldown(1, 5, commands.BucketType.guild)
async def checkmap(ctx, arg):

    embed.set_author(name="Mapcycle")
    
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

#wr checker, arg = map, arg2 = style, arg3 = track
@bot.command(aliases=["record", "mtop", "maptop", "maprecord"], brief="Gets the map record for a given map, style and track. Compares against SourceJump's best time if applicable.", usage="[map] <style> <(m)/b>")
#@commands.cooldown(1, 5, commands.BucketType.guild)
async def wr(ctx, arg, arg2, arg3):
    with a2s.ServerQuerier((IP, PORT)) as server:
        conn = mysql.connector.connect(**db)
        cursor = conn.cursor()

#download map function
@bot.command(aliases=["dl", "dm", "dlmap" "mapdl"], brief="Download a map using a GameBanana link, or map name.")
#@commands.cooldown(1, 5, commands.BucketType.guild)
async def downloadmap(ctx, arg):

    embed.colour = 0x35cbdb

    mapname = str(arg)
    
    #gamebanana method
    if mapname.startswith("https://gamebanana.com/mods/"):
        embed.set_author(name="Map Downloader - GameBanana")
        itemID = mapname.split("/")[4]

        #gb api stuff
        gbAPIRequest = requests.get(f"https://api.gamebanana.com/Core/Item/Data?itemtype=Mod&itemid={itemID}&fields=name,Files().aFiles()").json()
        gbName = gbAPIRequest[0]
        modID = list(gbAPIRequest[1])[0]
        mapfileName = gbAPIRequest[1].get(modID).get("_sFile")
        mapfileSize = gbAPIRequest[1].get(modID).get("_nFilesize")
        downloadURL = gbAPIRequest[1].get(modID).get("_sDownloadUrl")
        folderName = list(gbAPIRequest[1].get(modID).get("_aMetadata").get("_aArchiveFileTree"))[0]

        #attempt to get files within folder if applicable
        try:
            mapFiles = gbAPIRequest[1].get(modID).get("_aMetadata").get("_aArchiveFileTree").get(folderName)
        except AttributeError:
            mapFiles = gbAPIRequest[1].get(modID).get("_aMetadata").get("_aArchiveFileTree")

            embed.description = f"Downloading **{gbName}** from GameBanana, {size(mapfileSize)}..."
            msg = await ctx.send(embed=embed)

            async with aiohttp.ClientSession() as session:
                async with session.get(downloadURL) as resp:

                    mapFile = await aiofiles.open(f"{MAPS_FOLDER}/{mapfileName}", mode="wb")
                    await mapFile.write(await resp.read())
                    await mapFile.close()

                    embed.add_field(name="Contents:", value=mapFiles)        
                    embed.description = f"Extracting **{mapfileName}**..."
                    await msg.edit(embed=embed)

                    patoolib.extract_archive(f"{MAPS_FOLDER}/{mapfileName}", outdir=f"{MAPS_FOLDER}")

    #acer/sojourner method
    else:
        downloadURL = "http://sojourner.me/fastdl/maps/"
        sojournerFile = mapname + ".bsp.bz2"

        #check for bhop_ / kz_ / kz_bhop_
        for maptype in maptypes:
            if requests.head(f"{downloadURL}{maptype}{sojournerFile}").status_code == 200:

                embed.set_author(name="Map Downloader - Sojourner")
                embed.description = f"Downloading **{maptype}{sojournerFile}** from Sojourner.me..."
                msg = await ctx.send(embed=embed)

                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{downloadURL}{maptype}{sojournerFile}") as resp:

                        mapFile = await aiofiles.open(f"{MAPS_FOLDER}/{maptype}{sojournerFile}", mode="wb")
                        await mapFile.write(await resp.read())
                        await mapFile.close()  

                        embed.description = f"Extracting **{maptype}{sojournerFile}**..."
                        await msg.edit(embed=embed)

                        patoolib.extract_archive(f"{MAPS_FOLDER}/{maptype}{sojournerFile}", outdir=f"{MAPS_FOLDER}")

            else:
                pass





#cooldowns, remove the """s and the #s from the lines with @commands.cooldown to enable
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

@wr.error
async def wr_cooldown(ctx, error):
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