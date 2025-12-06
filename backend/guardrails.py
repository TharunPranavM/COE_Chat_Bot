def apply_guardrails(query, response):
    """
    Apply guardrails to filter harmful content while allowing legitimate academic discussions.
    Only blocks queries that are clearly requesting harmful actions, not educational content.
    """
    
    # Patterns that indicate harmful intent (not just mentioning the topic)
    harmful_patterns = [
        "how to make a bomb",
        "how to hack",
        "how to cheat on exam",
        "exam answers",
        "steal",
        "how to plagiarize",
        "help me cheat",
        "give me exam leak",
        "how to commit fraud",
        "how to discriminate",
        "ways to hurt",
        "how to kill"
    ]
    
    query_lower = query.lower()
    
    # Check if query is requesting harmful actions (not just mentioning topics)
    if any(pattern in query_lower for pattern in harmful_patterns):
        return (
            "I cannot provide assistance with that request. "
            "If you have questions about academic integrity, ethics, or safety, "
            "please consult with your instructor or appropriate authority."
        )
    
    # Allow the response through - the LLM system prompt already handles ethical responses
    return response