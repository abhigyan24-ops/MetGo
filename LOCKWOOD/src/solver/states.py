"""
Defines the possible induction states a train can be assigned to for
a single planning night.
"""

SERVICE = "service"
STANDBY = "standby"
MAINTENANCE = "maintenance"
CLEANING = "cleaning"

# BREAKDOWN represents an unplanned failure reported via manual override.
# It differs from MAINTENANCE (which is planned, schedulable upkeep tied to a job card).
# BREAKDOWN forces the train out of the service pool immediately, but the solver
# should NEVER choose it organically during normal planning; it is reachable
# exclusively via override.
BREAKDOWN = "breakdown"

ALL_STATES = [SERVICE, STANDBY, MAINTENANCE, CLEANING, BREAKDOWN]
