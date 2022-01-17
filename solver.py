import enum
from re import X
import numpy as np
import pandas as pd
from pulp import *
from itertools import product


# preferences: 3D array where [ta, day, time] is the utility gained by the
#              assignment of that TA to that (day, time) slot.
# slot_capacity: 2D array where [day, time] is the max number of TAs that
#                should be assigned to that slot
# ta_times: 1D array where [ta] is the max number of slots assigned to that TA
# day_min: 1D array where [day] is the minimum number of slots assigned that day
# day_max: 1D array, similar to above but for maximum
def schedule(preferences, ta_times, slot_capacity, day_min, day_max):
    preferences = np.array(preferences)
    ta_times = np.array(ta_times)
    slot_capacity = np.array(slot_capacity)
    num_ta, num_days, num_times = preferences.shape
    ###########################
    ##       Variables       ##
    ###########################
    slots = list(product(np.arange(num_days), np.arange(num_times)))
    paired_slots = [(day, time) for (day, time) in slots if time < num_times - 1]

    # For each TA, create variables representing possible assignment to each time slot
    variables = np.empty_like(preferences, dtype = object)
    for ta_idx in range(num_ta):
        for day_idx in range(num_days):
            for time_idx in range(num_times):
                variables[ta_idx, day_idx, time_idx] = \
                    LpVariable("TA{}_Day{}_Time{}".format(ta_idx, day_idx, time_idx),
                               cat = "Binary")

    # Dummy variable that is 1 iff the corresponding slot is double-booked
    doubled_vars = np.empty(shape = (num_days, num_times), dtype = object)
    for day_idx in range(num_days):
        for time_idx in range(num_times):
            doubled_vars[day_idx, time_idx] = \
                LpVariable("double_({}, {})".format(day_idx, time_idx),
                            cat = "Binary")

    # Dummy variable to encourage contiguous assignments
    # Variable is 1 iff both (day, time) and (day, time + 1) are assigned >= 1 TA
    contig_vars = np.empty(shape = (num_days, num_times - 1), dtype = object)
    for day_idx in range(num_days):
        for time_idx in range(num_times - 1):
            contig_vars[day_idx, time_idx] = \
                LpVariable("contig_({}, {})".format(day_idx, time_idx),
                            cat = "Binary")
    
    # Dummy variable used to ensure each TA is assigned only to adjacent OH slots
    # TODO: Generalize to remove implicit assumption that each block is 1 or 2 slots long
    ta_contig_vars = np.empty(shape = (num_ta, num_days, num_times - 1), dtype = object)
    for ta_idx in range(num_ta):
        for day_idx in range(num_days):
            for time_idx in range(num_times - 1):
                ta_contig_vars[ta_idx, day_idx, time_idx] = \
                    LpVariable("contig_({}, {}, {})".format(ta_idx, day_idx, time_idx),
                                cat = "Binary")

    # Dummy variable indicating that a pair is achieved
    #   (Duplicates may exist, to add more weight when a preference is
    #   expressed by both TAs in a pair)
    #   TODO: Ignore one-sided requests? (or weight them less?)
    #         (but that needs to be clear in the survey)
    desired_ta_pairs = pair_with_any(0, num_ta) + pair_with_any(1, num_ta) \
                        + [(4, 0), (4, 12)] + pair_with_any(10, num_ta) \
                        + [(11, 19), (11, 5), (11, 14)] \
                        + [(12, 4)] + [(14, 5), (14, 11)]
    ta_pair_at_time_var = np.empty(shape = (len(desired_ta_pairs), num_days, num_times),
                                   dtype = object)
    for pair_idx in range(len(desired_ta_pairs)):
        for day_idx in range(num_days):
            for time_idx in range(num_times):
                ta_pair_at_time_var[pair_idx, day_idx, time_idx] = \
                    LpVariable("pair_({}, {}, {})".format(pair_idx, day_idx, time_idx),
                                cat = "Binary")

    ta_pair_var = [LpVariable("pair_(TA{}, TA{})".format(ta1, ta2), cat = "Binary")
                    for (ta1, ta2) in desired_ta_pairs]
    
    ###########################
    ##      Constraints      ##
    ###########################
    constraints = []

    # Each OH slot can be occupied by at most slot_capacity[slot] TAs
    constraints += [lpSum(variables[:, day, time]) <= slot_capacity[day, time] \
                    for (day, time) in slots]

    # Each TA can be assigned to a maximum number of slots, based on ta_times
    constraints += [lpSum(variables[i, :, :].reshape(-1)) <= ta_times[i]
                    for i in range(num_ta)]

    # Each TA cannot be assigned to a slot with preference 0
    pref_zero_indices = np.argwhere(preferences == 0)
    constraints += [variables[tuple(i_tuple)] <= 0 for i_tuple in pref_zero_indices]

    # Each day has a minimum number of OH
    constraints += [lpSum(variables[:, day, :].reshape(-1)) >= day_min[day] \
                    for (day) in range(num_days)]

    # Each day has a maximum number of OH
    constraints += [lpSum(variables[:, day, :].reshape(-1)) <= day_max[day] \
                    for (day) in range(num_days)]


    # Each doubled_var is 1 iff the slot is double-booked
    # Constraint:
    #   (num TAs assigned to slot) - 1 <= var <= 0.5 * (num TAs assigned to slot)
    constraints += [doubled_vars[day, time] <= 0.5 * lpSum(variables[:, day, time])
                    for (day, time) in slots]
    constraints += [doubled_vars[day, time] >= -1 + lpSum(variables[:, day, time])
                    for (day, time) in slots]

    # Each contig_var is 1 iff both slots in the corresponding pair are assigned
    # Notice that (num TAs assigned - doubled_var) is 1 iff the slot is assigned
    # Constraint:
    #   (num slots assigned) - 1 <= var <= 0.5 * (num slots assigned)
    constraints += [contig_vars[day, time] <=
                            0.5 * (lpSum(variables[:, day, time])
                                - doubled_vars[day, time])
                            + 0.5 * (lpSum(variables[:, day, time + 1])
                                - doubled_vars[day, time + 1])
                        for (day, time) in paired_slots]

    constraints += [contig_vars[day, time] >= -1
                                + lpSum(variables[:, day, time])
                                    - doubled_vars[day, time]
                                + lpSum(variables[:, day, time + 1])
                                    - doubled_vars[day, time + 1]
                            for (day, time) in paired_slots]

    # Do not schedule during lecture times
    constraints += [lpSum(variables[:, day, time]) <= 0 for (day, time) in {(1, 0), (3, 0)}]

    # Do not schedule certain TAs during recitation
    tas_noon = [1, 10, 6, 8, 15, 18]
    tas_130pm = [1, 3, 2, 7]
    tas_3pm = [0, 12, 2, 9]
    tas_430pm = [16, 13, 11]
    tas_8pm = [21]
    constraints += [variables[ta, 3, 2 + offset] <= 0 for (ta, offset) in product(tas_noon, {-1, 0, 1})]
    constraints += [variables[ta, 3, 3 + offset] <= 0 for (ta, offset) in product(tas_130pm, {-1, 0, 1})]
    constraints += [variables[ta, 3, 4 + offset] <= 0 for (ta, offset) in product(tas_3pm, {-1, 0, 1})]
    constraints += [variables[ta, 3, 5 + offset] <= 0 for (ta, offset) in product(tas_430pm, {-1, 0, 1})]
    constraints += [variables[ta, 2, 7 + offset] <= 0 for (ta, offset) in product(tas_8pm, {-1, 0, 1})]

    # Enforce that ta_pair_var is 0 if there is no pair *anywhere* in the week
    # IMPLICIT: ta_pair_var will be 1 if possible, as it contributes + utility
    # TODO: Add this constraint explicitly, so that we can discourage certain pairs
    constraints += [ta_pair_at_time_var[i, day, time] <=\
                        0.5 * variables[ta1, day, time] + \
                        0.5 * variables[ta2, day, time]
                    for ((i, (ta1, ta2)), (day, time))
                        in product(enumerate(desired_ta_pairs), slots)]
    constraints += [ta_pair_var[pair_idx] <= lpSum(ta_pair_at_time_var[pair_idx, :, :])
                    for pair_idx in range(len(desired_ta_pairs))]

    
    # Monday OH must have >=1 TA in the afternoon
    constraints += [lpSum(variables[:, 0, time]) >= 1 for time in {3, 4, 5}]
    constraints += [lpSum(variables[:, 0, time]) >= 2 for time in {6, 7, 8}]

    # Constraints for personal requests
    constraints += [ta_pair_var[desired_ta_pairs.index((4, 12))] == 1] # Zetty and Diego

    constraints += [variables[20, 5, 1] == 1]  # Michael and Peak adjacent
    constraints += [variables[20, 5, 2] == 1]
    constraints += [variables[21, 5, 3] == 1]
    constraints += [variables[21, 5, 4] == 1]


    # Each TA is assigned only to adjacent OH slots AND each TA is assigned a max of 2 slots per day
    # TODO: Would be nice to generalize
    # 1) Each TA is assigned a maz of 2 slots per day ("Max2" criterion)
    constraints += [lpSum(variables[ta, day, :]) <= 2
                    for (ta, day) in product(range(num_ta), range(num_days))]

    # 2) ta_contig_vars is 0 unless both slots are assigned
    constraints += [ta_contig_vars[ta, day, time] <= 0.5 * variables[ta, day, time] \
                                                    + 0.5 * variables[ta, day, time + 1]
                    for (ta, (day, time)) in product(range(num_ta), paired_slots)]

    constraints += [ta_contig_vars[ta, day, time] >= -1 + variables[ta, day, time] \
                                                    + variables[ta, day, time + 1]
                    for (ta, (day, time)) in product(range(num_ta), paired_slots)]

    # 3) TAs are assigned to at most 1 "block" each day
    # Need to enforce: if lpSum(variables[ta, day, :]) == 2,
    #                  then lpSum(ta_contig_vars[ta, day, :]) == 1
    # By "Max2" criterion: if lpSum(variables[ta, day, :]) == 1,
    #                      then lpSum(ta_contig_vars[ta, day, :]) == 0
    constraints += [lpSum(variables[ta, day, :]) - lpSum(ta_contig_vars[ta, day, :]) <= 1
                    for (ta, day) in product(range(num_ta), range(num_days))]

    # I dislike 10:30pm – midnight office hours. Remove them.
    constraints += [lpSum(variables[:, :, 9]) == 0]
    ###########################
    ##       Objective       ##
    ###########################

    # Maximize preferences
    obj = lpDot(preferences.reshape(-1), variables.reshape(-1))

    # We prefer solutions that double-book TAs
    # obj += 1 * lpSum(doubled_vars)

    # We prefer solutions that assign contiguous office hours
    # Notice that contig_vars only deal with chunks of 2, but this is enough to
    #   encourage long chunks of office hours. For example, a chunk of 6
    #   contiguous OH will contribute +5 utility, whereas 3 chunks of 2
    #   contiguous OH will contribute only +3 utility.
    obj += 1 * lpSum(contig_vars)

    # Strongly prefer solutions with desired pairs
    obj += 3 * lpSum(ta_pair_var)

    ###########################
    ##     Solve Problem     ##
    ###########################
    prob = LpProblem("scheduleProblem", LpMaximize)
    prob += obj
    for constraint in constraints:
        prob += constraint
    prob.solve(GUROBI_CMD(msg = 1, timeLimit = 30))

    return variables

def output_soln(variables, preferences, ta_names, time_options, day_options):
    _, num_days, num_times = variables.shape
    slots = product(np.arange(num_days), np.arange(num_times))
    assignments = np.empty(shape = (num_days, num_times), dtype = object)
    for (day, time) in slots:
        assignments[day, time] = get_tas(variables, day, time, ta_names)

    for i, ta in enumerate(ta_names):
        print("---")
        print(ta)
        curr_assignments = variables[i, :, :]
        assignment_idices = np.nonzero(np.vectorize(value)(curr_assignments))
        print(preferences[i][assignment_idices])

    return pd.DataFrame(assignments.T, index = time_options, columns = day_options)

def get_tas(variables, day, time, ta_names):
    tas = []
    for i, var in enumerate(variables[:, day, time]):
        if value(var) == 1:
            tas.append(ta_names[i])

    return ", ".join(tas)

def pair_with_any(ta, num_tas):
    return [(ta, any_ta) for any_ta in range(num_tas) if any_ta != ta]