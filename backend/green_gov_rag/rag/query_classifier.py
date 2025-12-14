class QueryClassifier:
    def __init__(self):
        self.categories = {
            "emissions_reporting": ["emission", "carbon", "co2", "ghg"],
            "biodiversity": ["biodiversity", "ecosystem", "species"],
            "water_management": ["water", "river", "groundwater"],
            "waste_management": ["waste", "recycling", "landfill"],
            "mining": ["mining", "minerals", "excavation"],
            "agriculture": ["agriculture", "farming", "crop"]
        }

    def classify(self, query: str):
        query = query.lower()
        scores = {}

        for category, keywords in self.categories.items():
            scores[category] = sum(kw in query for kw in keywords)

        best = max(scores, key=scores.get)

        if scores[best] == 0:
            return {"query_category": "general", "confidence": 0.3}

        confidence = min(0.95, scores[best] / sum(scores.values()))

        return {
            "query_category": best,
            "confidence": round(confidence, 2)
        }
