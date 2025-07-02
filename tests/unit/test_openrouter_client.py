import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from src.ai.openrouter_client import OpenRouterClient, ModelResponse

class TestOpenRouterClient:
    """Test cases for OpenRouterClient"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        with patch('src.ai.openrouter_client.config') as mock:
            mock.openrouter.api_key = "test-api-key"
            mock.openrouter.base_url = "https://openrouter.ai/api/v1"
            mock.openrouter.default_model = "meta-llama/llama-3.1-8b-instruct:free"
            mock.openrouter.fallback_models = [
                "deepseek/deepseek-r1:free",
                "qwen/qwen-plus:free"
            ]
            mock.openrouter.http_referer = "https://test-app.com"
            mock.openrouter.app_title = "Test App"
            mock.app.max_retries = 3
            mock.app.response_timeout = 30
            mock.app.daily_request_limit = 50
            mock.app.enhanced_request_limit = 1000
            yield mock
    
    @pytest.fixture
    def client(self, mock_config):
        """Create OpenRouterClient instance"""
        with patch('src.ai.openrouter_client.OpenAI'):
            return OpenRouterClient()
    
    def test_client_initialization(self, mock_config):
        """Test client initialization"""
        with patch('src.ai.openrouter_client.OpenAI') as mock_openai:
            with patch('src.ai.openrouter_client.httpx') as mock_httpx:
                client = OpenRouterClient()
                
                # Check that OpenAI was called with the correct parameters
                args, kwargs = mock_openai.call_args
                assert kwargs['base_url'] == "https://openrouter.ai/api/v1"
                assert kwargs['api_key'] == "test-api-key"
                assert 'http_client' in kwargs  # Should have http_client for connection pooling
                
                assert client.usage_count == 0
                assert client.session_start <= time.time()
                assert hasattr(client, '_usage_lock')  # Should have thread lock
    
    def test_generate_response_success(self, client):
        """Test successful response generation"""
        # Mock the OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response content"
        
        client.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        messages = [
            {"role": "user", "content": "Test query"}
        ]
        
        content, model = client.generate_response(messages)
        
        assert content == "Test response content"
        assert model == "meta-llama/llama-3.1-8b-instruct:free"
        assert client.usage_count == 1
    
    def test_generate_response_with_fallback(self, client, mock_config):
        """Test response generation with fallback models"""
        # Mock the OpenAI client to fail on first model
        def side_effect(*args, **kwargs):
            if kwargs['model'] == "meta-llama/llama-3.1-8b-instruct:free":
                raise Exception("Model failed")
            else:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Fallback response"
                return mock_response
        
        client.client.chat.completions.create = MagicMock(side_effect=side_effect)
        
        messages = [{"role": "user", "content": "Test query"}]
        
        content, model = client.generate_response(messages)
        
        assert content == "Fallback response"
        assert model == "deepseek/deepseek-r1:free"
        assert client.usage_count == 1
    
    def test_generate_response_all_models_fail(self, client):
        """Test when all models fail"""
        client.client.chat.completions.create = MagicMock(
            side_effect=Exception("All models failed")
        )
        
        messages = [{"role": "user", "content": "Test query"}]
        
        with pytest.raises(Exception) as exc_info:
            client.generate_response(messages)
        
        assert "All models failed to respond" in str(exc_info.value)
    
    def test_generate_structured_response(self, client):
        """Test structured response generation"""
        # Mock generate_response
        client.generate_response = MagicMock(
            return_value=("Test content", "meta-llama/llama-3.1-8b-instruct:free")
        )
        
        messages = [{"role": "user", "content": "Test query"}]
        response = client.generate_structured_response(messages, "test_type")
        
        assert isinstance(response, ModelResponse)
        assert response.content == "Test content"
        assert response.model_used == "meta-llama/llama-3.1-8b-instruct:free"
        assert response.cost == 0.0  # Free model
        assert response.engine_used == "test_type"
        assert response.response_time > 0
    
    def test_check_rate_limits_basic(self, client, mock_config):
        """Test rate limit checking with basic account"""
        client.usage_count = 25
        client._has_enhanced_limits = MagicMock(return_value=False)
        
        limits = client.check_rate_limits()
        
        assert limits["daily_limit"] == 50
        assert limits["current_usage"] == 25
        assert limits["remaining_calls"] == 25
        assert limits["usage_percentage"] == 50.0
    
    def test_check_rate_limits_enhanced(self, client, mock_config):
        """Test rate limit checking with enhanced account"""
        client.usage_count = 100
        client._has_enhanced_limits = MagicMock(return_value=True)
        
        limits = client.check_rate_limits()
        
        assert limits["daily_limit"] == 1000
        assert limits["current_usage"] == 100
        assert limits["remaining_calls"] == 900
        assert limits["usage_percentage"] == 10.0
    
    def test_calculate_cost_paid_model(self, client):
        """Test cost calculation for paid models"""
        content = " ".join(["word"] * 750)  # ~1000 tokens
        model = "gpt-4"
        
        cost = client._calculate_cost(content, model)
        
        assert cost == pytest.approx(0.001, rel=0.1)
    
    def test_get_available_models(self, client, mock_config):
        """Test getting available models"""
        models = client.get_available_models()
        
        expected_models = [
            "meta-llama/llama-3.1-8b-instruct:free",
            "deepseek/deepseek-r1:free",
            "qwen/qwen-plus:free"
        ]
        
        assert models == expected_models
    
    def test_test_connection_success(self, client):
        """Test successful connection test"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OK"  # The optimized client expects "OK" in response
        
        client.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        result = client.test_connection()
        
        assert result is True
    
    def test_test_connection_failure(self, client):
        """Test failed connection test"""
        client.client.chat.completions.create = MagicMock(
            side_effect=Exception("Connection failed")
        )
        
        result = client.test_connection()
        
        assert result is False
    
    def test_headers_included_in_request(self, client, mock_config):
        """Test that headers are properly included in API request"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test"
        
        client.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        messages = [{"role": "user", "content": "Test"}]
        client.generate_response(messages)
        
        # Verify the call included the correct headers
        client.client.chat.completions.create.assert_called_with(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=messages,
            max_tokens=150,  # Default max_tokens
            temperature=0.3,  # Default temperature  
            extra_headers={
                "HTTP-Referer": "https://test-app.com",
                "X-Title": "Test App"
            },
            timeout=15.0  # Optimized client uses 15.0 timeout
        )