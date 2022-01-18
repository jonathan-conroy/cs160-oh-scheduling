import numpy as np
import pandas as pd
from solver import *
from pulp import *

# Parameters
official_name = "First name (official, according to Tufts) "
last_name = "Last name"
pref_name = "What you prefer to be called (if different from first name)"
question_names  = ["OH Availability (1st Preference)",
                    "OH Availability (2nd Preference)",
                    "OH Availability (3rd Preference)"]
preferences_scores = [3, 2, 1]
day_options     = ["Monday", "Tuesday", "Wednesday", "Thusday", "Friday",
                    "Saturday", "Sunday"]
time_options    = ["9:00 - 10:30 am", "10:30 - Noon", "Noon - 1:30 pm",
                    "1:30 - 3:00 pm", "3:00 - 4:30 pm", "4:30 - 6:00 pm",
                    "6:00 - 7:30 pm", "7:30 - 9:00 pm", "9:00 - 10:30 pm",
                    "10:30 - Midnight"]

# Setup
time_to_index = {time : i for (i, time) in enumerate(time_options)}
day_to_index = {day : i for (i, day) in enumerate(day_options)}
num_days = len(day_options)
num_times = len(time_options)


def parse_csv(filepath):
    # Setup
    data = pd.read_csv(filepath)
    num_tas = data.shape[0]
    
    # Construct preferences array
    preferences = np.zeros(shape = (num_tas, num_days, num_times))
    for (question_string, pref_score) in zip(question_names, preferences_scores):
        # For each preference (1st, 2nd, or 3rd), update the relevant `preferences` cells
        for ta_idx, row in data.iterrows():
            
            for time_idx, time_slot in enumerate(time_options):
                column_string = "{} [{}]".format(question_string, time_slot)

                if not pd.isna(row[column_string]):
                    pref_days = [day.strip() for day in row[column_string].split(",")]
                    for day_idx in [day_to_index[day] for day in pref_days]:
                        preferences[ta_idx, day_idx, time_idx] = pref_score
    
    # Construct TA names
    ta_names = [(row[official_name] if pd.isna(row[pref_name]) else row[pref_name]).strip() +
                " " + row[last_name].strip()
                for (_, row) in data.iterrows()]
    
    ta_max_times = [hours//1.5 for hours in data["Truncated OH"]]

    # Construct 
    print(preferences)
    return (preferences, ta_max_times, ta_names)


def validate_ta(ta_pref, ta_name):
    # Select 3 options for "1st preference"
    num_first = np.count_nonzero(ta_pref == preferences_scores[0])
    num_second = np.count_nonzero(ta_pref == preferences_scores[1])
    num_third = np.count_nonzero(ta_pref == preferences_scores[2])

    num_sunday = np.count_nonzero(ta_pref[day_to_index["Sunday"]] >= preferences_scores[1])
    num_monday = np.count_nonzero(ta_pref[day_to_index["Monday"]] >= preferences_scores[1])

    print(ta_name)
    valid = True
    if (num_first < 3):
        print("    Only {} first preferences".format(num_first))
        valid = False
    if (num_second < 3):
        print("    Only {} second preferences".format(num_second))
        valid = False
    if (num_third < 3):
        print("    Only {} third preferences".format(num_third))
        valid = False
    if (num_sunday + num_monday < 2):
        print("    Only {} peak hours".format(num_sunday + num_monday))
        print("    Sunday: {}, Monday: {}".format(num_sunday, num_monday))
        print(ta_pref[day_to_index["Monday"]])
        valid = False
    if valid:
        print("    Valid!")
    
    return valid
    

preferences, ta_max_times, names = parse_csv("/Users/jonathanconroy/Downloads/CS 160 TA Survey (Spring 2022) (Responses) - Form Responses 1.csv")
num_valid = 0
for i, name in enumerate(names):
    num_valid += validate_ta(preferences[i], name)
print("Valid/Total: {}/{}".format(num_valid, len(names)))
    
print("--------------")
print(ta_max_times)
slot_capacity = [[2 if day == "Monday" else 1 for _ in time_options] for day in day_options]
# for time in {3, 4, 5, 6, 7, 8}: # Allow some double-booking on Sunday
#     slot_capacity[6][time] = 2
day_min = [10, 2, 2, 3, 4, 5, 7]
day_max = [12, 5, 5, 6, 5, 10, 10]
vars = schedule(preferences, ta_max_times, slot_capacity, day_min, day_max)
output_df = output_soln(vars, preferences, names, time_options, day_options)
output_df.to_csv("oh_schedule_cs160.csv")