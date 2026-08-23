# Stay points and frequent places

The deterministic first version sorts samples by time, finds windows that remain within 100 m for at least 20 minutes, and uses their centroid as a stay point. Frequent places cluster stay centroids within 150 m. Ranking combines visit count (50%), dwell hours (scaled 3%), and a 14-day exponential recency term (30%).

The algorithm runs locally and does not require reverse geocoding. Labels are optional cached metadata. Tests use synthetic repeated home/work routines; production tuning must evaluate urban canyon accuracy and sampling gaps.

