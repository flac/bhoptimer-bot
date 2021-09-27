import aiofiles
import aioftp
import aiohttp
import bz2
import discord
import json
import mysql.connector
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

#fastdl related
FTP_IP = cfg["ftp_ip"]
FTP_USER = cfg["ftp_user"]
FTP_PASS = cfg["ftp_pass"]
FASTDL_FOLDER = cfg["fastdl_folder"]

#database related
DB_IP = cfg["db_ip"]
DB_USER = cfg["db_user"]
DB_PASS = cfg["db_pass"]
DB_DB = cfg["db_database"]

#discord related
ADMIN_IDS = cfg["admin_ids"]
THUMBNAIL = cfg["thumbnail"]
MAPS_CHANNEL = int(cfg["maps_channel"])

bot = commands.Bot(command_prefix=PREFIX)

db = {
  "user": DB_USER,
  "password": DB_PASS,
  "host": DB_IP,
  "database": DB_DB
}

maptypes = ["", "bhop_", "kz_", "kz_bhop_"]
valve.rcon.RCONMessage.ENCODING = "utf-8"

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

    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{server_name}")
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

                    #fixed the dumb method of finding bots thanks lorp
                    if re.search(r"BOT\s+active$", player):
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

            embed.add_field(name="Players:", value=finalList, inline=False)
            embed.add_field(name="Join Server:", value=f"steam://connect/{IP}:{PORT}", inline=False)
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
    
    if not serverOffline:

        if str(user.id) in ADMIN_IDS:
            with a2s.ServerQuerier((IP, PORT)) as server:
                
                command = valve.rcon.execute((IP, PORT), RCON_PW, " ".join(args[:]))
                
                embed = discord.Embed(colour=discord.Colour(0xcc9900), timestamp=datetime.utcnow(), description=f"```{command}```")
                embed.set_author(name="RCON")
                embed.set_footer(text=f"{server_name}")

                #send response as txt if over discord 2k chars limit (thanks chris)
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

#mapcycle checker
@bot.command(aliases=["mapcycle", "mapcheck"], brief="Check if specified map is in the mapcycle", usage="[map]")
#@commands.cooldown(1, 5, commands.BucketType.guild)
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

    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{server_name}")
    embed.colour = 0x35cbdb

    mapname = str(arg)
    mapsChannel = bot.get_channel(MAPS_CHANNEL)

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
            folderName = ""

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
            
                patoolib.extract_archive(f"{MAPS_FOLDER}/{mapfileName}", outdir=f"{MAPS_FOLDER}", interactive=False)

                #move files out of any folders to main maps folder
                for file in mapFiles:
                    shutil.move(f"{MAPS_FOLDER}/{folderName}/{file}", f"{MAPS_FOLDER}/{file}")

                embed.description = f"Compressing contents..."
                await msg.edit(embed=embed)
                
                compressedFiles = []

                #only want bsps, navs are small enough to be downloaded uncompressed
                for file in mapFiles:
                    if str(file).endswith('.bsp'):
                        with bz2.open(f"{MAPS_FOLDER}/{file}.bz2", "wb") as compressedFile:
                            with open(f"{MAPS_FOLDER}/{file}", "rb") as bsp:
                                data = bsp.read()
                                compressedFile.write(data)
                                compressedFiles.append(f"{file}.bz2")
                    else:
                        pass    

                embed.description = f"Moving files to FastDL..."
                embed.remove_field(0)
                await msg.edit(embed=embed)                        

                for file in compressedFiles:

                    if FTP_IP:
                        async with aioftp.Client.context(FTP_IP, user=FTP_USER, password=FTP_PASS) as ftp:
                            await ftp.upload(f"{MAPS_FOLDER}/{file}", f"{FASTDL_FOLDER}/{file}", write_into=True)

                        #cleanup
                        try:
                            os.remove(f"{MAPS_FOLDER}/{file}")
                            os.remove(f"{MAPS_FOLDER}/{mapfileName}")
                        #extracting zips with folders in them deletes the zip
                        except FileNotFoundError:
                            pass
                        
                        #delete folders if zip has one in it
                        if folderName:
                            try:
                                os.removedirs(f"{MAPS_FOLDER}/{folderName}")
                            except FileNotFoundError:
                                pass

                    else:
                        try:
                            #have to specify full path to overwrite existing
                            shutil.move(f"{MAPS_FOLDER}/{file}", f"{FASTDL_FOLDER}/{file}")

                            #cleanup
                            os.remove(f"{MAPS_FOLDER}/{mapfileName}")

                            #delete folders if zip has one in it
                            if folderName:
                                try:
                                    os.removedirs(f"{MAPS_FOLDER}/{folderName}")
                                except FileNotFoundError:
                                    pass
                                
                        #weird error even though all maps get moved in a mappack        
                        except FileNotFoundError:
                            pass
                
                #update mapcycle
                fileList = os.listdir(MAPS_FOLDER)
                with open(MAPCYCLE, "w") as mapCycleFile:
                    for file in fileList:
                        if str(file).endswith(".bsp"):
                            mapCycleFile.write(file[:-4] + "\n")  

                embed.description = f"Successfully added **{gbName}**."
                await msg.edit(embed=embed) 

                if MAPS_CHANNEL:
                    await mapsChannel.send(f"```Added {gbName}.```\n{mapname}")
                    
                else:
                    pass
        

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

                        patoolib.extract_archive(f"{MAPS_FOLDER}/{maptype}{sojournerFile}", outdir=f"{MAPS_FOLDER}", interactive=False)

                        embed.description = f"Moving **{maptype}{sojournerFile}** to FastDL..."
                        await msg.edit(embed=embed)                        

                        if FTP_IP:
                            async with aioftp.Client.context(FTP_IP, user=FTP_USER, password=FTP_PASS) as ftp:
                                await ftp.upload(f"{MAPS_FOLDER}/{maptype}{sojournerFile}", f"{FASTDL_FOLDER}/{maptype}{sojournerFile}", write_into=True)

                            #cleanup
                            os.remove(f"{MAPS_FOLDER}/{maptype}{sojournerFile}")
                        
                        else:
                            #have to specify full path to overwrite existing
                            shutil.move(f"{MAPS_FOLDER}/{maptype}{sojournerFile}", f"{FASTDL_FOLDER}/{maptype}{sojournerFile}")

                        #update mapcycle
                        fileList = os.listdir(MAPS_FOLDER)
                        with open(MAPCYCLE, "w") as mapCycleFile:
                            for file in fileList:
                                if str(file).endswith(".bsp"):
                                    mapCycleFile.write(file[:-4] + "\n")                       

                        embed.description = f"Successfully added **{maptype}{mapname}**."
                        await msg.edit(embed=embed) 

                        if MAPS_CHANNEL:
                            await mapsChannel.send(f"```Added {maptype}{mapname}.```\n{downloadURL}{maptype}{sojournerFile}")
                            
                        else:
                            pass
            else:
                embed.set_author(name="Map Downloader - Sojourner")
                embed.description = f"Unable to find map on Sojourner.me."
                embed.color = 0xd2222d
                msg = await ctx.send(embed=embed)
                break


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
