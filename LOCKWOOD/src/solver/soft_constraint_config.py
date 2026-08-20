"""
Configuration constants for Part 2's soft constraints, plus the new
Part 3a major-job-card soft constraint — thresholds and default
penalty weights.
"""

# --- Cleaning (Part 2a) ---
CLEANING_OVERDUE_DAYS = 3
CLEANING_PENALTY_WEIGHT = 10

# --- Branding (Part 2a) ---
BRANDING_PENALTY_WEIGHT = 1

# --- Wear-leveling (Part 2b) ---
WEAR_LEVELING_PENALTY_WEIGHT = 1

# --- Shunting (Part 2b) ---
SHUNTING_PENALTY_WEIGHT = 1

# --- Major job card (Part 3a, new) ---
# Flat penalty applied when a train with an open MAJOR-severity job
# card is assigned to service. Weighted higher than the cleaning
# penalty (10) since an unresolved major mechanical issue is a more
# serious concern than a cleaning delay, but this remains a soft
# preference, not a prohibition — only CRITICAL severity hard-blocks.
MAJOR_JOB_CARD_PENALTY_WEIGHT = 8

# --- Fitness cert expiring soon (Part 3b, new) ---
# A cert that is NOT yet expired (already-expired certs are hard-
# blocked, see model_builder.py) but will expire within this many
# days is a soft preference toward MAINTENANCE, not a prohibition --
# the train is still legal for service right up until PLANNING_DATE.
EXPIRING_SOON_DAYS = 7
# Flat penalty applied when such a train is assigned anything OTHER
# than MAINTENANCE. Placeholder weight, not tuned in this task --
# same status as the other flat weights above.
EXPIRING_SOON_PENALTY_WEIGHT = 6
