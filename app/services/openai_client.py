import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from pydantic import BaseModel


class OpenAIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        completion_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            completion_kwargs["max_tokens"] = max_tokens
        
        if response_format is not None:
            completion_kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**completion_kwargs)
        return response.choices[0].message.content
    
    def structured_completion(
        self,
        messages: List[Dict[str, str]],
        response_model: BaseModel,
        model: str = "gpt-4",
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        schema = response_model.model_json_schema()
        
        completion = self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": schema,
                    "strict": True
                }
            },
            **kwargs
        )
        
        try:
            return json.loads(completion)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse structured response: {e}")
    
    def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )


def get_openai_service() -> OpenAIService:
    if not hasattr(get_openai_service, '_instance'):
        get_openai_service._instance = OpenAIService()
    return get_openai_service._instance

# For backward compatibility
openai_service = None 