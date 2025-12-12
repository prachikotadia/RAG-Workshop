"""Groq/Llama API LLM client."""
from typing import List, Dict
import logging
from app.rag.chain import LlmClient
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)


class GroqLlmClient(LlmClient):
    """Groq API LLM client for Llama models."""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError("groq package not installed. Install with: pip install groq")
        return self._client
    
    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response from Groq."""
        client = self._get_client()
        
        async def _generate():
            import asyncio
            # Groq client is synchronous, so we need to run it in executor
            loop = asyncio.get_event_loop()
            # Convert messages to Groq format
            groq_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self.model,
                    messages=groq_messages,
                    temperature=0.8,  # Slightly higher for more natural, human-like responses
                    top_p=0.9  # Nucleus sampling for better quality
                )
            )
            
            return response.choices[0].message.content
        
        try:
            # Add timeout to prevent hanging
            import asyncio
            return await asyncio.wait_for(
                retry_async(_generate, max_retries=2, exceptions=(Exception,)),  # Reduced retries
                timeout=30.0  # 30 second timeout for LLM generation
            )
        except asyncio.TimeoutError:
            logger.error(f"Groq LLM generation timed out after 30 seconds")
            raise TimeoutError("LLM generation timed out")
        except Exception as e:
            logger.error(f"Error generating Groq LLM response: {e}", exc_info=True)
            raise
    
    async def stream(self, messages: List[Dict[str, str]]):
        """Stream response tokens from Groq."""
        client = self._get_client()
        
        async def _stream():
            import asyncio
            loop = asyncio.get_event_loop()
            groq_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            stream = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self.model,
                    messages=groq_messages,
                    temperature=0.8,
                    top_p=0.9,
                    stream=True
                )
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        try:
            import asyncio
            async for chunk in _stream():
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming Groq LLM response: {e}", exc_info=True)
            raise


class LocalLlmClient(LlmClient):
    """Local LLM client (LM Studio, Ollama, etc.)."""
    
    def __init__(self, base_url: str, model: str = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI-compatible client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self.base_url,
                    api_key="not-needed"  # Local LLMs don't need API keys
                )
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response from local LLM."""
        client = self._get_client()
        
        async def _generate():
            import asyncio
            # Local LLM client is synchronous, so we need to run it in executor
            loop = asyncio.get_event_loop()
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            # Use model from config or default
            model_name = self.model or "local-model"
            
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=model_name,
                    messages=openai_messages,
                    temperature=0.8,  # Slightly higher for more natural, human-like responses
                    top_p=0.9  # Nucleus sampling for better quality
                )
            )
            
            return response.choices[0].message.content
        
        try:
            # Add timeout to prevent hanging
            import asyncio
            return await asyncio.wait_for(
                retry_async(_generate, max_retries=2, exceptions=(Exception,)),  # Reduced retries
                timeout=30.0  # 30 second timeout for LLM generation
            )
        except asyncio.TimeoutError:
            logger.error(f"Local LLM generation timed out after 30 seconds")
            raise TimeoutError("LLM generation timed out")
        except Exception as e:
            logger.error(f"Error generating Local LLM response: {e}", exc_info=True)
            raise
    
    async def stream(self, messages: List[Dict[str, str]]):
        """Stream response tokens from local LLM."""
        client = self._get_client()
        
        async def _stream():
            import asyncio
            loop = asyncio.get_event_loop()
            openai_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            model_name = self.model or "local-model"
            stream = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=model_name,
                    messages=openai_messages,
                    temperature=0.8,
                    top_p=0.9,
                    stream=True
                )
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        try:
            import asyncio
            async for chunk in _stream():
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming local LLM response: {e}", exc_info=True)
            raise

