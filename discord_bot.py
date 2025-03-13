import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO
import calendar
import pytz
import discord
from dotenv import load_dotenv
import asyncio
from collections import Counter

est = pytz.timezone("US/Eastern")
BOT_RUNNING = False

active_channels = set()

load_dotenv()
client = discord.Client(intents=discord.Intents.all())


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        for c in guild.text_channels:
#            print(f"- {c.name} - {c.guild.name} -") #debug
            if c.name == "🏋︱fitness" and c.guild.name == "The Nerds":
                fitness_channel = c
                active_channels.add(fitness_channel)
            if c.name == "fitness" and c.guild.name == "r3inventing's server":
                test_channel = c
                active_channels.add(test_channel)
    
    for channel in active_channels:
        print(f"watching {channel.name} in guild {channel.guild}")

    try:
        global BOT_RUNNING
        if not BOT_RUNNING:
            print(f"- {fitness_channel} -")
            client.loop.create_task(weekly_tracker(client, fitness_channel))
            BOT_RUNNING = True
    except Exception as e:
        raise Exception(f"Failed to run the weekly tracker! {e}") from e


@client.event
async def on_message(message):
    """
    Main driver function. Gets invoked whenever the bot sees a message in its watched channels.
    Will filter out messages that it deems not revelant.
    Filters based on the active_channels set which is populated at bot runtime
    """

    #filter out irrelevant messages
    if message.author == client.user:
        return
    if message.channel not in active_channels:
        return

    #start weekly scheduler, if needed
    global BOT_RUNNING
    if not BOT_RUNNING:
        client.loop.create_task(weekly_tracker(client, message.channel))
        BOT_RUNNING = True

    #process relevant messages
    if "!checkin" in message.content.lower():
        # we need the local server nickname for display purposes
        local_server_nickname = await get_local_server_nickname(message, client)
        
        # we need to know the user's universal discord name to easily count their checkins
        universal_discord_name = message.author.name

        # in case the user doesn't have a nickname set up, just use their universal name
        if local_server_nickname is None:
            local_server_nickname = universal_discord_name

        count = 0
        today = datetime.now()
        today = today.replace(hour=0, minute=0, second=0)
        last_monday = est.localize(today + relativedelta(weekday=MO(-1)))
        if today.date() == last_monday.date():
            until_date = today + relativedelta(weekday=MO(+2)) - timedelta(seconds=1)
        else:
            until_date = today + relativedelta(weekday=MO(+1)) - timedelta(seconds=1)

        print(f"Counting checkings for {universal_discord_name} between dates {last_monday} and {until_date}")
        async for message in message.channel.history(after=last_monday, before=until_date, limit=None):
            if '!checkin' in message.content.lower() and message.created_at >= last_monday and message.author.name == universal_discord_name:
                count += 1
        
        fire_string = ''.join([':fire:' for _ in range(count)])
        workouts_or_workout = "workouts" if count > 1 else "workout"
        message_part_one = get_message_part_one(local_server_nickname)
        message_to_channel = message_part_one + \
            f"That's {count} {workouts_or_workout} since {calendar.day_name[last_monday.weekday()]}, {last_monday.strftime('%m-%d')}! \n" 
        message_to_channel += fire_string
        await message.channel.send(message_to_channel)

    if message.content == "!tracker":
        today = datetime.now() + timedelta(days=7)
        workouts = await get_tracker_information(client, message.channel, today)
        leaderboard = construct_leaderboard(workouts)
        message_to_channel = "Here's how we're doing so far this week! :thinking:\n\n" + leaderboard + "\nGreat work everyone! :heart:"
        No_leaderboard_message_to_channel = "Here's how we're doing so far this week! :thinking:\n\n https://media.tenor.com/VPT2-nyi42cAAAAd/what-happened-where-is-everyone.gif"
        
        if leaderboard == "":
            message_to_channel = No_leaderboard_message_to_channel
        
        print(message_to_channel)
        await message.channel.send(message_to_channel)
        
    """
    Used to redue the tracker if the bot was not running Monday morning to automaticly do it
    """
    if message.content == "!LastWeekTracker":
        today = datetime.now() + timedelta(days=365)
        workouts = await get_tracker_information(client, message.channel, today)
        leaderboard = construct_leaderboard(workouts)
        message_to_channel = "Here's what we did last week! :thinking:\n\n" + leaderboard + "\nGreat work everyone! :heart:"
        
        No_leaderboard_message_to_channel = "Here's what we did last week! :thinking:\n\n https://media.tenor.com/VPT2-nyi42cAAAAd/what-happened-where-is-everyone.gif"
        
        if leaderboard == "":
            message_to_channel = No_leaderboard_message_to_channel
        
        print(message_to_channel)
        await message.channel.send(message_to_channel)

    """
    Used to make a summary of the past year
    """
    if message.content == "!YearlyWrapup":
        datestart = datetime.now() + relativedelta(weekday=MO(-53))
        workouts = await get_tracker_info_for_range(client, message.channel, datestart, datetime.now())
        leaderboard = construct_leaderboard(workouts)
        message_to_channel = "Here's what we did last year! :thinking:\n\n" + leaderboard + "\nGreat work everyone! :heart:"
        
        No_leaderboard_message_to_channel = "Here's what we did last year! :thinking:\n\n https://media.tenor.com/VPT2-nyi42cAAAAd/what-happened-where-is-everyone.gif"
        
        if leaderboard == "":
            message_to_channel = No_leaderboard_message_to_channel
        
        print(message_to_channel)
        await message.channel.send(message_to_channel)



async def get_local_server_nickname(message, client):
    """
    Get local nickname so the bot displays the name that server users are expecting to see.
    """
    member_id = message.author.id
    guild_id = message.guild.id
    guild = await client.fetch_guild(guild_id)
    guild_member = await guild.fetch_member(member_id)
    local_server_name = guild_member.nick

    return local_server_name


async def weekly_tracker(client, channel):
    """
    Invokes the tracker automatically once a week on Monday morning.
    Will display all the checkins from all the users that were seen in the previous week.
    """
    today = datetime.now()
    next_monday = est.localize(today + relativedelta(weekday=MO(+1)))
    if today.date() == next_monday.date():
        next_monday = est.localize(today + relativedelta(weekday=MO(+2)))
    print(f"Weekly tracker running on channel {channel.guild}:{channel.name}! Next Monday is {next_monday.date()}")
    while True:
        workouts = {}
        today = datetime.now()
        if today.date() == next_monday.date():
            next_monday = est.localize(today + relativedelta(weekday=MO(+2)))
            print(f"Next time we check the leaderboard automatically should be {next_monday.date()}")
            workouts = await get_tracker_information(client, channel, today)
            message_to_channel = f":fire::fire::fire::fire::fire::fire::fire:\nHey, it's a new week! Let's see how we did!\n\nHere are the results from last week: \n\n"
            workout_results = construct_leaderboard(workouts)
            message_to_channel += workout_results
            message_to_channel += "\nKeep up the great work, everyone!\n:fire::fire::fire::fire::fire::fire::fire:"
            
            No_leaderboard_message_to_channel = "Hey, it's a new week! Let's see how we did!\n\n https://media.tenor.com/VPT2-nyi42cAAAAd/what-happened-where-is-everyone.gif"
            if workout_results == "":
                message_to_channel = No_leaderboard_message_to_channel
                
            print(message_to_channel)
            await channel.send(message_to_channel)
        await asyncio.sleep(3600) # check time every 3 hours
    

async def get_tracker_information(client, channel, input_date):
    """
    Populates a dictionary called "workouts".
    Tracks all the checkins we've seen from every user over the past week.
    In order to display this correctly, we need to go out and get the server nickname for every user we see.
    Then we map the server nicknames back to the universal Discord names so we can find checkins easily.
    """
    workouts = {}
    usernames = {}
    input_date = input_date.replace(hour=0, minute=0, second=0)
    after_date = input_date + relativedelta(weekday=MO(-2))
    until_date = input_date + relativedelta(weekday=MO(+1)) - timedelta(seconds=1)
    print(f"Getting !checkins from between {after_date} and {until_date}")
    async for m in channel.history(after=after_date, before=until_date, limit=None):
        # usernames dictionary is used to map the universal discord name to the local server nickname
        # so we can display things using names that people are expecting to see :)
        if m.author.name not in usernames:
            local_server_nickname = await get_local_server_nickname(m, client)
            usernames[m.author.name] = local_server_nickname if local_server_nickname else m.author.name
        if "!checkin" in m.content.lower():
            if usernames[m.author.name] in workouts:
                workouts[usernames[m.author.name]] += 1
            else:
                workouts[usernames[m.author.name]] = 1
        
    return workouts

async def get_tracker_info_for_range(client, channel, input_date1, input_date2):
    """
    Populates a dictionary called "workouts".
    Tracks all the checkins we've seen from every user over the past week.
    In order to display this correctly, we need to go out and get the server nickname for every user we see.
    Then we map the server nicknames back to the universal Discord names so we can find checkins easily.
    """
    workouts = {}
    usernames = {}
    input_date1 = input_date1.replace(hour=0, minute=0, second=0)
    input_date2 = input_date2.replace(hour=0, minute=0, second=0)
    after_date = input_date1
    until_date = input_date2 - timedelta(seconds=1)
    print(f"Getting !checkins from between {after_date} and {until_date}")
    async for m in channel.history(after=after_date, before=until_date, limit=None):
        # usernames dictionary is used to map the universal discord name to the local server nickname
        # so we can display things using names that people are expecting to see :)
        if m.author.name not in usernames:
            local_server_nickname = await get_local_server_nickname(m, client)
            usernames[m.author.name] = local_server_nickname if local_server_nickname else m.author.name
        if "!checkin" in m.content.lower():
            if usernames[m.author.name] in workouts:
                workouts[usernames[m.author.name]] += 1
            else:
                workouts[usernames[m.author.name]] = 1
        
    return workouts

def construct_leaderboard(workout_dict):
    """
    Construct the leaderboard/tracker. This will display at the beginning of every week (Monday morning),
    but can also be invoked with the !tracker command
    """
    workout_counter = Counter(workout_dict)
    return_string = ''
    for person in workout_counter.most_common():
        workouts_or_workout = "workouts" if person[1] > 1 else "workout"
        workout_result = f"{person[0]}: {person[1]} {workouts_or_workout}!\n"
        return_string += workout_result

    return return_string


def get_message_part_one(local_server_nickname):
    part_one_options = [
        f"Hey, nice workout, {local_server_nickname}!\n",
        f"Looking great, {local_server_nickname}! :star_struck:\n",
        f"You're on fire, {local_server_nickname}! :heart_on_fire:\n",
        f"So proud of you, {local_server_nickname}! :muscle:\n",
        f"Another one in the books, {local_server_nickname}! :white_check_mark:\n",
        f"So workout! Much strong! :dog:\n",
        f"You're a rockstar, {local_server_nickname}! :sunglasses:\n",
        f":clap: Let's hear it for {local_server_nickname}! :clap:\n",
        f"Doing great, {local_server_nickname}! Keep it up!\n",
        f"Great workout, {local_server_nickname}! I'm so inspired!\n",
        f"Killing it, {local_server_nickname}!\n",
        f"So happy to see you, {local_server_nickname}! :heart:\n",
        f"What a machine! :mechanical_arm:\n",
        f"Woohoo! Great work, {local_server_nickname}:bangbang:\n",
        f"Look at you, working on you! :heart_eyes:\n",
        f"Getting fit as a fiddle, {local_server_nickname}! :violin:\n",
        f"You inspire me, {local_server_nickname}! :star_struck:\n",
        f"You're a star, {local_server_nickname}! :stars:\n",
        f"You're doing great things, {local_server_nickname}! :metal:\n"
    ]
    part_one = random.choice(part_one_options)

    return part_one

# run the bot
with open("bot_token", "r") as file:
    bot_token = file.read()

client.run(bot_token)
