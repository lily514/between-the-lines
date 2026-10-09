"""Learner storage: where each viewer's record is kept between runs.

Everything goes through the `LearnerStore` protocol, so the storage can change (local JSON
files now, Azure Cosmos DB in Milestone 3) without touching the learning logic.
"""
