import os
import json
import aioftp
import shutil
import logging
import discord
import aiohttp
import requests
import aiofiles
import patoolib
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from discord.errors import HTTPException
from hurry.filesize import size

with open("config.json", "r") as config:
    cfg = json.load(config)

maptypes = ["", "bhop_", "kz_", "kz_bhop_"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
}

_log = logging.getLogger("discord")

intents = discord.Intents.default()
intents.message_content = True
bot: commands.Bot = commands.Bot(command_prefix=cfg["prefix"], intents=intents)

async def move_ftp(ctx, msg, embed, maps, name):
    for map in maps:
        if cfg['ftp_ip']:
            async with aioftp.Client.context(cfg['ftp_ip'], user=cfg['ftp_user'], password=cfg['ftp_pass']) as ftp:
                await ftp.upload(f"{map}", f"{cfg['fastdl_folder']}/{map}", write_into=True)
            os.remove(map)
        else:
            shutil.move(f"{map}", f"{cfg['fastdl_folder']}/{map}")
    embed.description = f"Successfully added **{name}**"
    await msg.edit(embed=embed)



async def fastdl_me(ctx, url, name):
    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_author(name="Map Downloader - fastdl.me")
    embed.description = f"Downloading **{name}** from fastdl.me..."
    embed.set_thumbnail(url=cfg["thumbnail"])
    embed.set_footer(text=f"balls")
    embed.colour = 0x35cbdb
    msg = await ctx.send(embed=embed)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            async with aiofiles.open(f"{name}.bsp.bz2", mode="wb") as map_file:
                await map_file.write(await resp.read())
            
            embed.description = f"Extracting **{name}.bsp.bz2**..."
            await msg.edit(embed=embed)

            patoolib.extract_archive(f"{name}.bsp.bz2", outdir=f"{cfg['maps_folder']}", interactive=False)

            embed.description = f"Moving **{name}.bsp.bz2** to FastDL..."
            await msg.edit(embed=embed)     
            await move_ftp(ctx, msg, embed, [f'{name}.bsp.bz2'], name)

async def gamebanana_dl(ctx, item_id):
    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_author(name="Map Downloader - GameBanana")
    embed.set_thumbnail(url=cfg["thumbnail"])
    embed.set_footer(text=f"balls")
    embed.colour = 0x35cbdb
    #gb api stuff
    gb_api_request = requests.get(f"https://api.gamebanana.com/Core/Item/Data?itemtype=Mod&itemid={item_id}&fields=name,Files().aFiles(),Preview().sSubFeedImageUrl()").json()
    gb_name = gb_api_request[0]
    mod_id = list(gb_api_request[1])[0]
    map_file_name = gb_api_request[1].get(mod_id).get("_sFile")
    map_file_size = gb_api_request[1].get(mod_id).get("_nFilesize")
    download_url = gb_api_request[1].get(mod_id).get("_sDownloadUrl")
    thumbnail = gb_api_request[2]
    map_files_request = requests.get(f"https://gamebanana.com/apiv11/File/{mod_id}/RawFileList")
    map_files = map_files_request.text.split("\n") 
    _log.info("map_files: %s", map_files)
    
    os.mkdir("temp")
    
    #attempt to get files within folder if applicable
    try:
        map_folder = map_files[0].split("/")[0]
        map_files = [x.split("/")[1] for x in map_files]
    except IndexError:
        map_folder = ""

    embed.set_thumbnail(url=thumbnail)
    embed.description = f"Downloading **{gb_name}**,\n**Size**: {size(map_file_size)}..."
    msg = await ctx.send(embed=embed)

    async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as resp:
            async with aiofiles.open(f"temp/{map_file_name}", mode="wb") as map_file:
                await map_file.write(await resp.read())

            embed.add_field(name="Contents:", value='\n'.join(map_files))        
            embed.description = f"Extracting **{map_file_name}**..."
            await msg.edit(embed=embed)

            patoolib.extract_archive(f"temp/{map_file_name}", outdir=f"temp/", interactive=False)
            
            #move files out of any folders to main maps folder
            for file in map_files:
                shutil.move(f"temp/{map_folder}/{file}", f"{cfg['maps_folder']}/{file}")        

            embed.description = f"Compressing contents..."
            await msg.edit(embed=embed)

            compressed_files = []

            #only want bsps, navs are small enough to be downloaded uncompressed
            for file in map_files:
                if str(file).endswith('.bsp'):
                    patoolib.create_archive(f"{file}.bz2", [f"{cfg['maps_folder']}/{file}"], interactive=False)
                    compressed_files.append(f"{file}.bz2")

            #cleanup
            shutil.rmtree("temp")

            embed.description = f"Moving files to FastDL..."
            embed.remove_field(0)
            await msg.edit(embed=embed)
            await move_ftp(ctx, msg, embed, compressed_files, gb_name)


@bot.command(aliases=["dl", "dm", "dlmap" "mapdl"], brief="Download a map using a GameBanana link, or map name.")
@commands.cooldown(1, 10, commands.BucketType.default)
async def download_map(ctx: commands.Context, url: str):

    _log.info("url: %s", url)
    if "https://gamebanana.com/mods/" in url:
        item_id = url.split("/")[4]
        _log.info("item_id: %s", item_id)
        await gamebanana_dl(ctx, item_id)

    else:
        balls = False
        for maptype in maptypes:
            download_url = f"http://main.fastdl.me/maps/{maptype}{url}.bsp.bz2"
            _statuscode = requests.head(download_url, headers=headers).status_code
            _log.info("download_url: %s, status_code: %s", download_url, _statuscode)
            if _statuscode == 302:
                balls = True
                break

        if balls:
            await fastdl_me(ctx, download_url, f"{maptype}{url}")
        else:
            raise Exception(f"Couldnt find map ({url})")

@download_map.error
async def error(ctx, error):
    embed = discord.Embed(timestamp=datetime.utcnow())
    embed.set_thumbnail(url=cfg['thumbnail'])
    embed.set_author(name="Error")
    embed.set_footer(text=f"balls")
    embed.colour = 0xd2222d
    embed.description = f"{error}"
    await ctx.send(embed=embed)

bot.run(cfg["token"], log_level=logging.INFO)
