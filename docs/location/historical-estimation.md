# Historical location estimation

`LocationEstimationService` ranks known frequent places and normalizes their scores into transparent confidence values. Future iterations may add weekday and time-of-day likelihood, but estimates must always remain `HISTORICAL_ESTIMATE`. They are never rendered or serialized as current GPS, and an empty history returns no estimate rather than a fabricated location.

