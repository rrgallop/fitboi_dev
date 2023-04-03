# FitBoi

Python bot used by community Discord server, developed in an attempt to track, encourage and reward the fitness pursuits of community members.

FitBoi tracks workouts posted by users by scanning the text for matching commands. He retrieves all of the messages from the past week and counts up how many contain certain recognized strings. Then, he messages the channel to let you know how well you're doing!

At the close of every week, early in the morning on each Monday, FitBoi will also create an aggregate report of all the checkins he has seen in the past week, and will post it in the channel to congratulate everyone for participating.

## Recognized commands

Currently, fitboi will respond to 2 commands:
1. `!checkin`: Lets FitBoi know that you have performed a workout! FitBoi will congratulate you on your accomplishment, and let you know how many workouts you've posted since the previous Monday.
2. `!tracker`: Aggregates and displays all the checkins from the most recent Monday through the current date.
