import discord
from discord.ext import commands
import youtube_dl
import os
from dbQuery import BAN as ban
import asyncio
from crawling_YT import Crawling_YT_Title, Crawling_YT_Comment
from mutagen.mp3 import MP3
import dbQuery

intent = discord.Intents.default()
intent.typing = False
intent.presences = False
intent.members = True

client = commands.Bot(command_prefix="!", intent = intent)
queue = list()           #제목 큐(대기열)
url_queue = list()       #url 큐(대기열)
searched_title = list()  #크롤링을 통해 유튜브에서 검색된 결과 5개(제목) 리스트
searched_url = list()    #크롤링을 통해 유튜브에서 검색된 결과 5개(url) 리스트
now_playing = str()


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
    def remove_song(self) :
        song_there = os.path.isfile("song.mp3")
        try :
            if song_there :
                os.remove("song.mp3")
        except PermissionError:
            print("PermissionError occured while deletion")
            return
    def download_song(self, url) :
        song_there = os.path.isfile("song.mp3")
        try :
            if song_there :
                os.remove("song.mp3")
        except PermissionError:
            print("PermissionError occured while deletion")
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


@client.command(
    # ADDS THIS VALUE TO THE $HELP PING MESSAGE.
	help="!help q",
	# ADDS THIS VALUE TO THE $HELP MESSAGE.
	brief="!help "
)

#큐의 목록을 메시지로 반환
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

#아티스트의 목록을 메시지로 반환
@client.command()
async def artist(ctx) :
    buf = 'List of artists in DB\n'
    buf += dbQuery.READ()
    await ctx.send(buf)


#자동재생 - Spotify의 API를 이용해 Artist의 Top10 음악을 큐에 저장 및 재생
@client.command()
async def auto(ctx, input : str = '') :
    global now_playing
    input_is_valid_num = False
    global searched_title
    global searched_url

    def after_song(err):                            #현재 재생중인 곡이 끝나면 다음곡을 재생하기 위한 재귀함수
        try :
            if len(queue) > 0:
                now_playing = queue[0]
                next_song = url_queue.pop(0)
                queue.pop(0)
                song_manager = Song()
                _video_title = song_manager.do_both(next_song)
                voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
                # now_playing = _video_title
            else:
                now_playing = queue[0]
                url_queue.pop(0)
                queue.pop(0)
                # now_playing = _video_title
                return
        except IndexError :
            pass

    try :
        converted_input = int(input)
        if type(converted_input) is not int :
            raise ValueError
        elif converted_input >= 1 and converted_input <= 31 :
            input_is_valid_num = True
    except ValueError :
        pass

    if input == '' :
        await ctx.send("Enter Artist name. To see list of artists, enter !artist")
        return
    elif input_is_valid_num :
        if not client.voice_clients :   #봇이 음성채널에 없음
            voiceChannel = ctx.author.voice.channel
            await voiceChannel.connect()
        artist_list = dbQuery.READ_FOR_DISCORD()
        searched_title.clear()
        searched_url.clear()
        import fetch_playlist as fetcher
        fetch_result = fetcher.fetch(artist_list[converted_input-1])
        print(fetch_result)
        now_playing = fetch_result[0]
        buf = 'Added song list\n'
        i = 1
        word = str()
        for var in fetch_result :
            word = artist_list[converted_input-1] + var
            searched_title, searched_url = Crawling_YT_Title(word)
            queue.append(var)
            url_queue.append(searched_url[0])
            buf = buf + '[' + str(i) + ']' + ' ' + var + '\n'
            i += 1
        await ctx.send(buf)

        song_manager = Song()
        song_manager.remove_song()
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)


#봇이 음성채널에 연결되어있는지를 확인
@client.command()
async def is_connected(ctx) :
    if client.voice_clients :
        await ctx.send("State : connected")
    else :
        await ctx.send("State : not connected")

#crawling_YT.py를 이용해 제목과 url을 가져오는 메소드
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

#음악 재생
@client.command()
async def play(ctx, *, input : str = '') :          #input이 다중인자일 수 있으므로 *를 인자로 줌(공백 포함)
    global now_playing
    voiceChannel = ctx.author.voice.channel         #메시지 작성자(유저)의 음성채널
    input_is_valid_num = False
    connection_state = False                        #connection_state : 봇이 음성채널에 연결되어있는지 확인하기 위한 변수
    if input == '':
        await ctx.send("Empty parameter")
        return
    if client.voice_clients :                       #봇이 음성채널에 있으면 connection_state를 True로 변경
        connection_state = True

    def after_song(err):                            #현재 재생중인 곡이 끝나면 다음곡을 재생하기 위한 재귀함수
        try :
            if len(queue) > 0:
                now_playing = _video_title
                now_playing = queue[0]
                queue.pop(0)
                song_manager = Song()
                _video_title = song_manager.do_both(next_song)
                voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
                # now_playing = _video_title
            else:
                now_playing = queue[0]
                url_queue.pop(0)
                queue.pop(0)
                # now_playing = _video_title
                return
        except IndexError :
            pass

    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    
    try :
        converted_input = int(input)
        if type(converted_input) is not int :
            raise ValueError
        elif converted_input >= 1 and converted_input <= 5 :
            input_is_valid_num = True
    except ValueError :
        pass
    
    if connection_state is True and not voice.is_playing() and not queue :      #봇이 음성채널에 연결됨 && 음악 재생중이 아님 && 큐가 비어있음 -> 다운로드, 재생, 재생중인 곡 타이틀 알려줌
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            youtube_search(ctx, input)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), connect, method play(재생), nowplaying()
            song_manager = Song()
            _video_title = song_manager.do_both(searched_url[converted_input-1])
            queue.clear()
            # queue.append(video_title)

            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
            now_playing = _video_title
            await ctx.send("Now playing : {}" .format(now_playing))

    elif connection_state is True and not voice.is_playing() and queue :        #봇이 음성채널에 연결됨 && 음악 재생중이 아님 && 큐가 비어있지 않음 -> queue에서 가져옴, 다운로드, 재생, 재생중인 곡 타이틀 알려줌
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            buf = youtube_search(ctx, input)                                    #queue의 첫 번째 원소를 Youtube에 검색해 상위 5개의 결과를 메시지로 리턴함
            await ctx.send(buf)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), method play(재생), nowplaying()
            song_manager = Song()
            video_title = song_manager.do_both(searched_url[converted_input-1])
            video_url = searched_url[int(input)-1]
            # queue.append(video_title)
            url_queue.append(video_url)

            if not queue :  #queue is empty
                await ctx.send("Queue is empty")

    elif connection_state is False :                                            #봇이 음성채널에 연결되지 않음
        queue.clear()
        await voiceChannel.connect()
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        if input_is_valid_num is False :                                        #사용자의 메시지가 1부터 5의 값이 아닌 경우, 즉 제목을 입력한 경우 -> input값을 title인자로 넘겨 유튜브 검색 상위 5개 검색결과 가져옴
            buf = youtube_search(ctx, input)
            await ctx.send(buf)
        else :                                                                  #사용자의 메시지가 1부터 5의 값인 경우 -> class Song(기존 파일 삭제, 번호에 맞는 음악 다운로드), connect, method play(재생), nowplaying()
            song_manager = Song()
            _video_title = song_manager.do_both(searched_url[converted_input-1])
            queue.clear()
            # queue.append(video_title)
            voice.play(discord.FFmpegPCMAudio("song.mp3"), after=after_song)
            now_playing = _video_title
            await ctx.send("Now playing : {}" .format(_video_title))

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

# #현재 재생중인 곡
# @client.command()
# async def nowplaying(ctx) :
#     global now_playing
#     if now_playing :
#         await ctx.send("Now playing : {}" .format(now_playing))
#     else :
#         await ctx.send("Currently no audio is playing.")

#봇을 음성채널에서 내보냄
@client.command()
async def leave(ctx):
    queue.clear()
    url_queue.clear()
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if client.voice_clients :
        voice.stop()
        await voice.disconnect()
    else :
        await ctx.send("The bot is not connected to a voice channel.")


#음악 일시정지
@client.command()
async def pause(ctx):
    try:
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
    except Exception:
        await ctx.send("Currently no audio is playing.")

#음악 재개
@client.command()
async def resume(ctx):
    try:
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
    except Exception:
        await ctx.send("The audio is not paused.")

#음악 중지
@client.command()
async def stop(ctx):
    try:
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        queue.clear()
        url_queue.clear()
        voice.stop()
    except Exception:
        await ctx.send("The bot is not connected.")

@client.command() #채팅채널 메세지 삭제 커맨드
async def clear(ctx, amount):
    await ctx.channel.purge(limit=int(amount)+1)#삭제 커맨트 인자 수 만큼 삭제+삭제커맨드메세지 포함 하여 삭제(+1)

@client.command()
async def banlist(ctx):#금지어 목록 출력 커맨드
    banlist = ban.BANREAD() #dbQuery.py의 BAN클래스 에 정의된 BANREAD() 호출 BAN 테이블에 저장된 금지어 목록리턴
    if banlist != []: #데이터베이스의 금지어 목록이 비어있는지 확인
        await ctx.send(banlist)#지정된 금지어 리스트 출력
    else:
        await ctx.send("banlist's empty")

@client.command()
async def addban(ctx, msg): #금지어목록 추가
    banlist = ban.BANREAD() #데이터베이스의 금지어 목록을 가져옴
    if msg in banlist:      #추가하려는 금지어가 데이터베이스의 금지어 목록에 있는지 확인
        await ctx.send("이미 목록에 있습니다.")
    else:
        ban.BANINSERT(msg)  #금지어 추가를위해 BANINSERT()호출 인자로 금지어 msg 전달
        await ctx.send(ban.BANREAD()) #추가 후 금지어 목록 호출

@client.command()
async def delban(ctx, msg): #금지어목록 삭제
    banlist = ban.BANREAD()
    if msg in banlist:  #삭제할 금지어가 데이터베이스에 있는지 확인
        ban.BANDELETE(msg)  #BANDELETE() 호출하여 금지어 삭제
        await ctx.send(msg+"삭제")
        await ctx.send(ban.BANREAD())   #삭제 후 금지어 목록 호출
    else:
        await ctx.send("목록에 없습니다.")

@client.command()
async def unmute(ctx, name):#채팅밴 언뮤트 명령어
    user = await ctx.guild.fetch_member(int(name[3:21])) #입력한 멘션아이디에서 멤버 아이디만 슬라이싱
    await ctx.channel.set_permissions(user,overwrite=None) #슬라이싱한 멤버아이디로 언뮤트
    await ctx.send(str(user)+" unmute!")

@client.command()
async def banuserlist(ctx): #채팅벤 데이터베이스 출력 명령어
    banuser, banusercount = ban.BANUSERREAD()   #데이터베이스 읽어오기
    if banuser:
        for i in range(len(banuser)):       #가져온 데이터베이스 만큼 반복
            await ctx.send(banuser[i]+"\tban count = "+str(banusercount[i])) #유저 밴카운트 출력
    else:
        await ctx.send("banuserlist's empty")

@client.command() 
async def delbanuser(ctx, name):    #밴카운트 초기화 명령어(db에서 삭제)
    user = await ctx.guild.fetch_member(int(name[3:21]))
    ban.BANUSERDELETE(str(user))
    await ctx.send(str(user)+" 밴 카운트 초기화")

@client.event
async def on_message(ctx):
    banlist = ban.BANREAD()
    user = ctx.author
    if any([word in ctx.content for word in banlist]):#금지어 삭제 기능
        if ctx.author == client.user:   #금지어 목록 출력을 위해 봇이 쓰는 금지어는 pass
            pass
        elif ctx.content.startswith(client.command_prefix+"delban"):#메세지 시작이 !delban명령어일 경우
            await client.process_commands(ctx) #명령어 실행
        else:   #봇 이외에 금지어를 사용하면 메세지를 삭제하고 경고문 출력
            banuser, banusercount = ban.BANUSERREAD()   #채팅밴 데이터베이스 읽어오기
            userstr = str(user) #멤버형 변수는 사용하기 까다롭기때문에 문자열로 변환
            if userstr in banuser:  #금지어를 사용한멤버가 데이터베이스에 있다면(2번이상 사용자)
                ban.BANUSERUPDATE(userstr,banusercount[banuser.index(userstr)])#업데이트 명령어
                await ctx.channel.send(userstr+"\tban count = "+str((banusercount[banuser.index(userstr)]+1)))

                if banusercount[banuser.index(userstr)]+1 > 4: #밴카운트가 5번 이상
                    await ctx.channel.set_permissions(user,send_messages=False) #채팅금지(MUTE)
                    ban.BANUSERDELETE(userstr)  #채팅금지 후 데이터베이스에서 삭제
                    await ctx.channel.send(userstr+"MUTE!")
            else:
                ban.BANUSERINSERT(userstr, int(1)) #금지어 사용이 처음인경우 데이터베이스 삽입
                await ctx.channel.send(userstr+"\tban count = "+ '1')

            await ctx.delete()
            await ctx.channel.send("That Word Is Not Allowed To Be Used! Continued Use Of Mentioned Word Would Lead To Punishment!")
    else:
        await client.process_commands(ctx)

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
            reaction, _r_user = await client.wait_for('reaction_add', timeout=5.0, check = chk_user)
        except asyncio.TimeoutError:
            emb2.add_field(name="Time out", value="처음부터 다시 입력해주세요")
            await ctx.send(embed=emb2)
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

client.run('YOUR_TOKEN')    #YOUR_TOKEN