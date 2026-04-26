"""
classifier.py
Tier-1 intent classifier for routing user messages
Cheap YandexGPT Lite call to classify: GREETING, CASUAL, or TEACHING
"""

import aiohttp
import asyncio
import logging
from config import (
    YANDEX_API_KEY, 
    YANDEX_FOLDER_ID, 
    YANDEX_MODEL_URI_LITE,
    CLASSIFIER_PROMPT
)

logger = logging.getLogger(__name__)


async def classify_intent(user_message: str, timeout: float = 10.0) -> str:
    """
    Classify user message intent using YandexGPT Lite (async mode)
    
    This is Tier-1 routing: cheap call to decide if we need expensive teaching call
    
    Args:
        user_message: User's input text
        timeout: Max wait time in seconds (default 10.0)
        
    Returns:
        "GREETING" - for hi, hello, привет
        "CASUAL" - for thanks, how are you, casual chat
        "TEACHING" - for actual English learning questions
        
    On failure: Returns "TEACHING" (safer to process than to block)
    
    Cost: ~50 tokens (~0.01 rubles) vs 650 tokens for full teaching call
    """
    
    # Build classifier prompt
    full_prompt = CLASSIFIER_PROMPT + user_message
    
    # Prepare API request for YandexGPT Lite
    request_data = {
        "modelUri": YANDEX_MODEL_URI_LITE,
        "completionOptions": {
            "temperature": 0,  # Deterministic classification
            "maxTokens": 10    # Only need one word response
        },
        "messages": [
            {
                "role": "user",
                "text": full_prompt
            }
        ]
    }
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID
    }
    
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            # Submit async request
            async with session.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync",
                headers=headers,
                json=request_data
            ) as response:
                
                if response.status != 200:
                    logger.error(f"Classifier API error: {response.status}")
                    return "TEACHING"
                
                result = await response.json()
                operation_id = result['id']
                logger.info(f"Classifier request submitted, operation_id: {operation_id}")
            
            # Poll for result
            result_url = f"https://llm.api.cloud.yandex.net/operations/{operation_id}"
            
            for attempt in range(20):  # Try 20 times (10 seconds total)
                await asyncio.sleep(0.5)
                
                async with session.get(result_url, headers=headers) as poll_response:
                    if poll_response.status != 200:
                        continue
                    
                    poll_data = await poll_response.json()
                    
                    if poll_data.get('done'):
                        # Extract answer
                        answer = poll_data['response']['alternatives'][0]['message']['text'].strip().upper()
                        
                        # Validate response
                        if answer in ["GREETING", "CASUAL", "TEACHING"]:
                            logger.info(f"Classified as: {answer}")
                            return answer
                        else:
                            logger.warning(f"Invalid classifier response: {answer}, defaulting to TEACHING")
                            return "TEACHING"
            
            # Timeout - polling exhausted
            logger.warning(f"Classifier polling timeout, defaulting to TEACHING")
            return "TEACHING"
                    
    except asyncio.TimeoutError:
        logger.warning(f"Classifier timeout after {timeout}s, defaulting to TEACHING")
        return "TEACHING"
        
    except Exception as e:
        logger.error(f"Classifier error: {str(e)}, defaulting to TEACHING")
        return "TEACHING"
