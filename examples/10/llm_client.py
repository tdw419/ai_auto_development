"""
LLM Client for LM Studio Integration
Handles API calls to local or remote LM Studio instance
"""

import requests
import json
from typing import Optional, Dict, Any, List
import time


class LMStudioClient:
    """
    Client for interacting with LM Studio's OpenAI-compatible API
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "local-model",
        timeout: int = 300
    ):
        """
        Initialize LM Studio client
        
        Args:
            base_url: LM Studio API endpoint
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        stream: bool = False
    ) -> str:
        """
        Generate completion from LM Studio
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            stream: Whether to stream response
            
        Returns:
            Generated text
        """
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        
        if stop:
            payload["stop"] = stop
        
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unexpected response format: {result}")
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"LM Studio request timed out after {self.timeout}s")
        
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to LM Studio: {e}")
    
    def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Generate with automatic retry on failure
        
        Args:
            prompt: Input prompt
            max_retries: Maximum retry attempts
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate(prompt, **kwargs)
            
            except (TimeoutError, ConnectionError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"LM Studio error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        raise last_error
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Multi-turn chat interface
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional generation parameters
            
        Returns:
            Assistant's response
        """
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2000),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False
        }
        
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def check_connection(self) -> bool:
        """
        Verify LM Studio is accessible
        
        Returns:
            True if connected, False otherwise
        """
        
        try:
            url = f"{self.base_url}/models"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available models in LM Studio
        
        Returns:
            List of model names
        """
        
        url = f"{self.base_url}/models"
        response = self.session.get(url, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        return [model["id"] for model in result.get("data", [])]


class Embedder:
    """
    Wrapper for text-embedding-qwen3-embedding-0.6b or any embedding model
    """
    
    def __init__(
        self,
        model_name: str = "text-embedding-qwen3-embedding-0.6b",
        base_url: str = "http://localhost:1234/v1",
        embedding_dim: int = 768
    ):
        """
        Initialize embedder
        
        Args:
            model_name: Embedding model name
            base_url: API endpoint
            embedding_dim: Expected embedding dimension
        """
        self.model_name = model_name
        self.base_url = base_url
        self.embedding_dim = embedding_dim
        self.session = requests.Session()
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        
        # Truncate very long text
        if len(text) > 8000:
            text = text[:8000]
        
        url = f"{self.base_url}/embeddings"
        
        payload = {
            "model": self.model_name,
            "input": text
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if "data" in result and len(result["data"]) > 0:
                embedding = result["data"][0]["embedding"]
                
                # Validate dimension
                if len(embedding) != self.embedding_dim:
                    print(f"Warning: Expected {self.embedding_dim} dims, got {len(embedding)}")
                
                return embedding
            else:
                raise ValueError(f"Unexpected embedding response: {result}")
        
        except requests.exceptions.RequestException as e:
            # Fallback: return zero vector
            print(f"Embedding error: {e}. Returning zero vector.")
            return [0.0] * self.embedding_dim
    
    def embed_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Embed multiple texts in batches
        
        Args:
            texts: List of input texts
            batch_size: Number to process at once
            
        Returns:
            List of embedding vectors
        """
        
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for text in batch:
                embeddings.append(self.embed(text))
            
            # Rate limiting
            if i + batch_size < len(texts):
                time.sleep(0.5)
        
        return embeddings


class MockLLMClient:
    """
    Mock LLM client for testing without LM Studio
    """
    
    def __init__(self):
        self.call_count = 0
    
    def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        
        # Generate mock response based on prompt content
        if "DEFECT" in prompt.upper():
            return """
IMPLEMENTATION:
Fixed the bug by updating the validation logic in utils.py

FILES_CHANGED:
- src/utils.py
- tests/test_utils.py

VERIFICATION_HINTS:
- Check that validation now handles edge cases
- Run test suite to verify fixes

SUMMARY:
Updated validation to handle null inputs and added corresponding tests.
"""
        
        return f"""
IMPLEMENTATION:
Completed the requested task successfully.

FILES_CHANGED:
- src/main.py
- src/helpers.py

VERIFICATION_HINTS:
- Verify code follows style guidelines
- Check that all tests pass

SUMMARY:
Implemented the requested functionality with proper error handling and tests.
"""
    
    def generate_with_retry(self, prompt: str, **kwargs) -> str:
        return self.generate(prompt, **kwargs)
    
    def check_connection(self) -> bool:
        return True


class MockEmbedder:
    """
    Mock embedder for testing
    """
    
    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
    
    def embed(self, text: str) -> List[float]:
        # Generate deterministic fake embedding
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        
        # Create pseudo-random but deterministic vector
        import random
        random.seed(hash_val)
        return [random.random() for _ in range(self.embedding_dim)]
    
    def embed_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        return [self.embed(text) for text in texts]
