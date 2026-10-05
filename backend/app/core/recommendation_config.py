"""Recommendation engine configuration (§26): ranking weights are configurable,
documented, and NOT presented as scientifically validated."""
RANKING_WEIGHTS = {
    # how much the student's overall risk raises priority
    "risk": 0.30,
    # severity of the specific weak area (0-1)
    "severity": 0.25,
    # recency of decline (recent drops score higher)
    "recent_decline": 0.15,
    # how well the matched resource fits the weak area's topic/type
    "resource_relevance": 0.15,
    # difficulty fit (resources slightly above current level score best)
    "difficulty_fit": 0.10,
    # historical usefulness of similar recommendations (from feedback)
    "feedback": 0.05,
}

# risk probability at/below which recommendations are light-touch
LOW_RISK_PROBABILITY = 0.15

# how many recommendations to persist per prediction
MAX_RECOMMENDATIONS = 6

# difficulty progression used for difficulty_fit scoring
DIFFICULTY_ORDER = ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
