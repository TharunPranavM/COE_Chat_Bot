def apply_guardrails(query, response):
    harmful_keywords = ["hate", "violence", "illegal"]
    if any(word in query.lower() for word in harmful_keywords):
        return "Query blocked for safety reasons."
    if any(word in response.lower() for word in harmful_keywords):
        return "Response moderated for safety."
    return response