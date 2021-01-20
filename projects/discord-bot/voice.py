import discord
from discord.ext import commands
import youtube_dl
import os
# from dbQuery import BAN as ban
import asyncio
from crawling_YT import Crawling_YT_Title, Crawling_YT_Comment
from mutagen.mp3 import MP3

client = commands.Bot(command_prefix=";")
queue = list()           #현재 큐안의 제목 
url_queue = list()       #현재 큐안의 url
searched_title = list()  #검색 리스트 5개
searched_url = list()    #검색 리스트 5개
now_play = ""

class Song :
    def __init__(self) :
        ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
        }
        self.ydl_opts = ydl_opts
    def download_song(self, url) :
        song_there = os.path.isfile("song.mp3")
        try :
            if song_there :
                os.remove("song.mp3")
        except PermissionError:
            return

        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([url])
        for file in os.listdir("./"):
            if file.endswith(".mp3"):
                os.rename(file, "song.mp3")
    def get_title(self, url) :
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', None)
        return video_title
    def do_both(self, url) :
        self.download_song(url)
        return self.get_title(url)


@client.command()
async def q(ctx) :
    buf = str()
    i = 1
    if queue :
        for var in queue :
            buf = buf + '[' + str(i) + ']' + ' ' + var + '\n'
            i += 1
        await ctx.send("Queue list\n{}" .format(buf))
    else :
        await ctx.send("Queue is empty")


@client.command()
async def artist(ctx) :
    import dbQuery
    buf = 'List of artists in DB'
    buf += dbQuery.READ()
    await ctx.send(buf)


@client.command()
async def auto(ctx, name : str = '') :
    if name == '' :
        await ctx.send("Enter Artist name. To see list of artists, enter !artist")
        return
    import fetch_playlist as fetcher
    for var in fetcher.fetch() :
        queue.append(var)
    buf = 'Added song list\n'
    i = 1
    for var in queue :
        buf = buf + '[' + str(i) + ']' + ' ' + var + '\n'
        i += 1
    await ctx.send(buf)


@client.command()
async def is_connected(ctx) :
    if client.voice_clients :
        await ctx.send("State : connected")
    else :
        await ctx.send("State : not connected")

def youtube_search(ctx, title) :
    global searched_title
    global searched_url
    i = 1
    buf = 'Search Results\n'
    searched_title.clear()
    searched_url.clear()
    searched_title, searched_url = Crawling_YT_Title(title)
    for var in searched_title :
        buf = buf + '[' + str(i) + ']' + ' ' + var + '\n'
        i += 1
    return buf


@client.command()
async def play(ctx, input : str = '') :
    # global queue                                #queue변수를 local메소드에서 사용하기 위함
    voiceChannel = ctx.author.voice.channel     #메시지 작성자(유저)의 음성채널
    input_is_valid_num = False
    connection_state = False                    #connection_state : 봇이 음성채널에 연결되어있는지 확인하기 위한 변수
    if client.voice_clients :                   #봇이 음성채널에 있으면 connection_state를 True로 변경
        connection_state = True

    def after_song(err):
        if len(queue) > 0:
            next_song = url_queue.pop(0)
            now_play = queue.pop(0)
            song_manager = Song()
            _video_title = song_manager.do_both(next_song)
            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
        else:
            return

    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    
    try :
        converted_input = int(input)
        if type(converted_input) is not int :
            raise ValueError
        elif converted_input >= 1 and converted_input <= 5 :
            input_is_valid_num = True
            selection = converted_input
    except ValueError :
        pass
    
    if connection_state is True and not voice.is_playing() :                    #봇이 음성채널에 연결됨 && 음악 재생중이 아님
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            buf = youtube_search(ctx, input)
            await ctx.send(buf)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), method play(재생), nowplaying()
            song_manager = Song()
            video_url = searched_url[int(input)-1]
            video_title = song_manager.do_both(video_url)
            queue.clear()
            queue.append(video_title)

            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
            
    elif connection_state is True and not voice.is_playing() and not queue :    #봇이 음성채널에 연결됨 && 음악 재생중이 아님 && 큐가 비어있음 -> 음성채널에 연결, 다운로드, 재생, 재생중인 곡 타이틀 알려줌
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            youtube_search(ctx, input)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), connect, method play(재생), nowplaying()
            song_manager = Song()
            video_title = song_manager.do_both(searched_url[converted_input-1])
            queue.clear()
            queue.append(video_title)

            await voiceChannel.connect()
            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
            await ctx.send("Now playing : {}" .format(str(queue[0])))

    elif connection_state is True and not voice.is_playing() and queue :        #봇이 음성채널에 연결됨 && 음악 재생중이 아님 && 큐가 비어있지 않음 -> queue에서 가져옴, 다운로드, 재생, 재생중인 곡 타이틀 알려줌
        await ctx.send(Crawling_YT_Title(queue[0]))                             #queue의 첫 번째 원소를 Youtube에 검색해 상위 5개의 결과를 메시지로 리턴함
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            youtube_search(ctx, input)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), method play(재생), nowplaying()
            song_manager = Song()
            video_title = song_manager.do_both(searched_url[converted_input-1])
            video_url = searched_url[int(input)-1]
            queue.append(video_title)
            url_queue.append(video_url)

            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
            await ctx.send("Now playing : {}" .format(str(queue[0])))

            if not queue :  #queue is empty
                await ctx.send("Queue is empty")

    elif connection_state is False :
        queue.clear()
        await voiceChannel.connect()
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            buf = youtube_search(ctx, input)
            await ctx.send(buf)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), connect, method play(재생), nowplaying()
            song_manager = Song()
            video_title = song_manager.do_both(searched_url[converted_input-1])
            queue.clear()
            queue.append(video_title)
            
            song_manager = Song()
            video_title = song_manager.do_both(searched_url[converted_input-1])
            queue.clear()
            queue.append(video_title)

            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
            await ctx.send("Now playing : {}" .format(str(queue[0])))

    elif voice.is_playing():
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            buf = youtube_search(ctx, input)
            await ctx.send(buf)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), method play(재생), nowplaying()
            song_manager = Song()
            video_url = searched_url[int(input)-1]
            video_title = song_manager.do_both(video_url)
            url_queue.append(video_url)
            queue.append(video_title)


@client.command()
async def nowplaying(ctx) :
    if queue :
        await ctx.send("Now playing : {}" .format(now_play))
    else :
        await ctx.send("Queue is empty")


@client.command()
async def leave(ctx):
    # voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    # if voice.is_connected():
    #     await voice.disconnect()
    # else:
    #     await ctx.send("The bot is not connected to a voice channel.")

    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if client.voice_clients :
        await voice.disconnect()
    else :
        await ctx.send("The bot is not connected to a voice channel.")


@client.command()
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        await ctx.send("Currently no audio is playing.")


@client.command()
async def resume(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
    else:
        await ctx.send("The audio is not paused.")


@client.command()
async def stop(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    voice.stop()


@client.command()
async def comment(ctx, url:str):
    #입력한 str이 url일 경우
    if url.find("youtube.com/watch") > -1:
        yt_id, yt_comment, yt_like = Crawling_YT_Comment(url)
        if len(yt_id)>10:
            yt_id, yt_comment, yt_like = yt_id[:10], yt_comment[:10], yt_like[:10]
        emb = discord.Embed(title="TOP 10 Comments",description="This is comment about {}".format(url),color=discord.Color.blue())
        emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        for i in range(len(yt_id)):
            emb.add_field(name="{} (🧡{})".format(yt_id[i], yt_like[i]), value="{}".format(yt_comment[i]),inline=False)
        if len(yt_id)==0:
            emb.add_field(name="Error or No comment", value="Please check the url")
        await ctx.send(embed=emb)

    #입력한 str이 검색어일 경우
    else:
        reaction_list = ['\U00000031\U0000FE0F\U000020E3','\U00000032\U0000FE0F\U000020E3','\U00000033\U0000FE0F\U000020E3','\U00000034\U0000FE0F\U000020E3','\U00000035\U0000FE0F\U000020E3']
        def chk_user(reaction, us):
            return us == ctx.author and reaction.message.id == re_msg.id
        
        titles, hrefs = Crawling_YT_Title(url)
        emb1 = discord.Embed(title="Select the title", description = "Select the number", color=discord.Color.dark_blue())
        for i in range(len(titles)):
            emb1.add_field(name="{}번".format(i+1), value="{}".format(titles[i]), inline=False)

        #반응을 누르기위해 기본반응 추가
        re_msg = await ctx.send(embed=emb1)
        for i in reaction_list:
            await re_msg.add_reaction(i)

        emb2 = discord.Embed(title="Youtube", description="" ,color=discord.Color.dark_blue())
        try:
            reaction, _r_user = await client.wait_for('reaction_add', timeout=30.0, check = chk_user)
        except asyncio.TimeoutError:
            emb2.add_field(name="Time out", value="처음부터 다시 입력해주세요")
            ctx.send(embed=emb2)
            return
        else:
            num = 0
            if str(reaction) == reaction_list[0]:
                num = 0
            elif str(reaction) == reaction_list[1]:
                num = 1
            elif str(reaction) == reaction_list[2]:
                num = 2
            elif str(reaction) == reaction_list[3]:
                num = 3
            elif str(reaction) == reaction_list[4]:
                num = 4

            yt_id, yt_comment, yt_like = Crawling_YT_Comment(hrefs[num])
            if len(yt_id)>10:
                yt_id, yt_comment, yt_like = yt_id[:10], yt_comment[:10], yt_like[:10]
            emb2 = discord.Embed(title="TOP 10 Comments",description="This is comment about {}".format(url),color=discord.Color.blue())
            emb2.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            for i in range(len(yt_id)):
                emb2.add_field(name="{} (🧡{})".format(yt_id[i], yt_like[i]), value="{}".format(yt_comment[i]),inline=False)
            if len(yt_id)==0:
                emb2.add_field(name="Error or No comment", value="Please check the url")
            await ctx.send(embed=emb2)
            return

client.run('Nzk4NDY1MzE4MTEyNDYwODIw.X_1axg.eZttz7QQ-I3sjFE8vuI8MKA3fyY')