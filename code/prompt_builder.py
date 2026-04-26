"""
prompt_builder.py
Build dynamic context and combine with static prompt
"""

from config import STATIC_PROMPT, LANGUAGE_BY_GRADE, MAX_SENTENCES_BY_GRADE


def build_dynamic_context(grade: int, textbook: str, user_message: str, 
                         conversation_history: list) -> str:
    """
    Build dynamic context from user state and conversation history
    
    Args:
        grade: User's grade (1-11)
        textbook: User's textbook (e.g., "Spotlight Grade 5" or "Unknown edition")
        user_message: Current user question
        conversation_history: List of (user_msg, bot_msg) tuples
        
    Returns:
        Formatted dynamic context string
    """
    # Get grade-specific language instruction
    language_instruction = LANGUAGE_BY_GRADE.get(grade, "mixed Russian/English")
    
    # Get grade-specific sentence limit
    max_sentences = MAX_SENTENCES_BY_GRADE.get(grade, "10")
    
    # Format conversation history
    history_str = ""
    if conversation_history:
        for user_msg, bot_msg in conversation_history:
            # Limit each message to first 150 chars to save tokens
            user_short = user_msg[:150] + "..." if len(user_msg) > 150 else user_msg
            bot_short = bot_msg[:150] + "..." if len(bot_msg) > 150 else bot_msg
            history_str += f"User: {user_short}\nBot: {bot_short}\n\n"
    else:
        history_str = "[No previous conversation]\n\n"
    
    # Build complete dynamic context
    dynamic_context = f"""Student: Grade {grade}
Textbook: {textbook}

Recent conversation:
{history_str}
Current question: {user_message}

Remember: Use {language_instruction} for this grade. Max {max_sentences} sentences."""
    
    return dynamic_context


def build_full_prompt(grade: int, textbook: str, user_message: str, 
                     conversation_history: list) -> str:
    """
    Combine static prompt with dynamic context
    
    Args:
        grade: User's grade (1-11)
        textbook: User's textbook
        user_message: Current user question
        conversation_history: List of (user_msg, bot_msg) tuples
        
    Returns:
        Complete prompt ready for API call
    """
    # Build dynamic part
    dynamic = build_dynamic_context(grade, textbook, user_message, conversation_history)
    
    # Combine static + dynamic
    full_prompt = f"""{STATIC_PROMPT}

---

{dynamic}"""
    
    return full_prompt


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of tokens in text
    
    Rule of thumb: 1 token ≈ 0.75 words for English/Russian mix
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count
    """
    word_count = len(text.split())
    # Conservative estimate: 1.3 tokens per word for Russian/English mix
    return int(word_count * 1.3)
