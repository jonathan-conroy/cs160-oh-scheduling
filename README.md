# CS160 Office Hour Scheduling
Formulates office hour assignments (for CS160 Spring 2022) as an integer programming problem. 

## Input for each TA:
- Number of hours desired
- 1st, 2nd, and 3rd preference office hour times
- Other notes (e.g. other TAs they wish to work with or not work with)

## Variables:
For every `(ta, day, time)` tuple, there is a binary variable that is 1 iff the
specified TA is assigned to the office hour slot at the day and time.
There are additional ``dummy variables'' used as indicators of certain conditions (e.g. a variable that is 1 if a certain slot is double-booked and 0 otherwise).

## Constraints:
- Every slot can have at most 1 TA, except on Monday (when slots can have 2 TAs)
- Every TA is assigned a number of office hours equal to their desired amount.
- A TA cannot be assigned to a slot that is not listed as a 1st, 2nd, or 3rd preference
- Each day has a minimum number of TA-hours
- Each day has a maximum number of TA-hours
- Monday must have >=1 TA in the afternoon
- Certain slots on Monday must have 2 TAs
- Each TA is assigned a maximum of 2 OH slots per day
- Each TA is only assigned adjacent OH slots on a given day (note that the current implementation of this constraint depends on the fact that each TA has at most 2 OH slots per day)
- No TA is assigned to a slot in which they have recitation, nor are they assigned to a slot _adjacent to_ their recitation.
- No office hours are held during lecture.

## Objective:
We maximize the sum of the following:
- Weighted sum of the number of 1st, 2nd, and 3rd preference assignments over all TAs (where 1st preference assignments contribute the most amount of utility)
- Sum of the number of pairs of adjacent office hours assigned (e.g. if noon–1:30, 1:30–3:00, and 3:00–4:30 are all assigned, add +2 utility).
- Number of pairs of TAs assigned to work together who requested to work together (by request, this can also be added as a constraint)

We use the GUROBI solver, which is able to find an optimal solution to problems of this sort in under 1 second.

## Comments for the Future:
Though I initially had concerns over unbalanced assignments (e.g. one TA getting all their 1st preferences and another TA getting all their 3rd preferences), the solutions produced mostly assigned 1st choice slots. The final schedule assigned 40 TA-hours, with 32 1st preference slots, 8 2nd preference slots, and no 3rd preference slots. Notably, the TAs who were assigned 2nd preference slots often had some secondary request (e.g. working with another TA) that was fulfilled. I'm not sure if this is a feature of this particular instance, or if this tends to be the case in general (I'd guess that it holds in general).

The [input collection form](https://docs.google.com/forms/d/e/1FAIpQLSfIxw73Y9wubVrlUL43lKokPicyh3dIc1X0SOGz0SE55SES7Q/viewform?usp=sf_link) was not great. There were overcomplicated instruction about the number of 1st/2nd/3rd preferences to select and about peak hours, and they did not serve much purpose. A better idea would be to ask for 1st and 2nd preferences (or similar), followed by a question asking for _all_ availability. It was also somewhat unclear how to model requests for people asking to work with another TA: is it better to assign two TAs to different 1st preference slots, or to assign them to the same 3rd preference slot? A better question might ask _how much_ a TA would like to work with another, giving the above example.

It would be interesting to poll students on their preferred office hour times and incorporate this into assignments (probably generating a tradeoff curve for student vs TA utility).

Some minimal manual tweaking was necessary after to ensure proper coverage (in this case, moving one TA to a less preferred slot to increase coverage during peak hours). It could be nice to have some visualization tool to easily identify TA preferences when making these adjustments.

