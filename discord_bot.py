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

load_dotenv()
client = discord.Client(intents=discord.Intents.all())

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(f"I am a member of {guild.name}:{guild.id}")

@client.event
async def on_message(message):
    #filter out irrelevant messages
    if message.author == client.user:
        return
    if str(message.channel) != "fitness":
        return

    #start weekly scheduler
    global BOT_RUNNING
    if not BOT_RUNNING:
        client.loop.create_task(weekly_tracker(message))
    BOT_RUNNING = True

    #process relevant messages
    if "!checkin" in message.content.lower():
        guild_id = message.guild.id
        member_id = message.author.id
        guild = await client.fetch_guild(guild_id)
        member_name = await guild.fetch_member(member_id)
        count = 0
        today = datetime.now()
        today = today.replace(hour=0, minute=0, second=0)
        last_monday = est.localize(today + relativedelta(weekday=MO(-1)))
        if today.date() == last_monday.date():
            until_date = today + relativedelta(weekday=MO(+2)) - timedelta(seconds=1)
        else:
            until_date = today + relativedelta(weekday=MO(+1)) - timedelta(seconds=1)
        print(f"Counting checkings for {author_name} between dates {last_monday} and {until_date}")
        async for message in message.channel.history(after=last_monday, before=until_date, limit=None):
            if '!checkin' in message.content.lower() and message.created_at >= last_monday and message.author.name == author_name:
                count += 1
        
        fire_string = ''.join([':fire:' for _ in range(count)])
        workouts_or_workout = "workouts" if count > 1 else "workout"
        message_to_channel = f"Hey, nice workout, {author_name}! \n"
        message_to_channel += "That's {count} {workouts_or_workout} since {calendar.day_name[last_monday.weekday()]}, {last_monday.strftime('%Y-%m-%d')}! \n" 
        message_to_channel += fire_string
        await message.channel.send(message_to_channel)

    if message.content == "!tracker":
        today = datetime.now() + timedelta(days=7)
        workouts = await get_tracker_information(message, today)
        leaderboard = construct_leaderboard(workouts)
        message_to_channel = "Here's how we're doing so far this week! :thinking:\n\n" + leaderboard + "\nGreat work everyone! :heart:"
        print(message_to_channel)
        await message.channel.send(message_to_channel)


async def weekly_tracker(message):
    today = datetime.now()
    next_monday = est.localize(today + relativedelta(weekday=MO(+2)))

    while True:
        workouts = {}
        today = datetime.now()
        if today.date() == next_monday.date():
            next_monday = est.localize(today + relativedelta(weekday=MO(+2)))
            print(f"Next time we check the leaderboard automatically should be {next_monday.date()}")
            workouts = await get_tracker_information(message, today)
            message_to_channel = f":fire::fire::fire::fire::fire::fire::fire:\nHey, it's a new week! Let's see how we did!\n\nHere are the results from last week: \n\n"
            workout_results = construct_leaderboard(workouts)
            message_to_channel += workout_results
            message_to_channel += "\nKeep up the great work, everyone!\n:fire::fire::fire::fire::fire::fire::fire:"
            print(message_to_channel)
            await message.channel.send(message_to_channel)
        await asyncio.sleep(3600)
    
async def get_tracker_information(message, input_date):
    workouts = {}
    input_date = input_date.replace(hour=0, minute=0, second=0)
    after_date = input_date + relativedelta(weekday=MO(-2))
    until_date = input_date + relativedelta(weekday=MO(+1)) - timedelta(seconds=1)
    print(f"Getting !checkins from between {after_date} and {until_date}")
    async for m in message.channel.history(after=after_date, before=until_date, limit=None):
        if m.author.name != "FitBoi" and "!checkin" in m.content.lower():
            if m.author.name in workouts:
                workouts[m.author.name] += 1
            else:
                workouts[m.author.name] = 1

    return workouts

def construct_leaderboard(workout_dict):
    workout_counter = Counter(workout_dict)
    return_string = ''
    for person in workout_counter.most_common():
        workouts_or_workout = "workouts" if person[1] > 1 else "workout"
        workout_result = f"{person[0]}: {person[1]} {workouts_or_workout}!\n"
        return_string += workout_result

    return return_string

with open("bot_token", "r") as file:
    bot_token = file.read()

client.run(bot_token)
