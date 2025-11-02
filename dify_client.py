"""
Dify API client for interacting with EventAIC workflow.
"""
import requests
import json
import time
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DifyAPIClient:
    """Client for interacting with Dify API."""
    
    def __init__(self, base_url: str, api_key: str, polling_interval: int = 2):
        """
        Initialize Dify API client.
        
        Args:
            base_url: Base URL for Dify API
            api_key: API key for authentication
            polling_interval: Interval in seconds for polling streaming responses
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.polling_interval = polling_interval
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def _parse_streaming_response(self, response_text: str) -> List[Dict]:
        """
        Parse streaming response from Dify API.
        
        Args:
            response_text: Raw response text from streaming API
            
        Returns:
            List of parsed event dictionaries
        """
        events = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('data: '):
                try:
                    data_str = line[6:]  # Remove 'data: ' prefix
                    event_data = json.loads(data_str)
                    events.append(event_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse event data: {e}")
                    continue
        
        return events
    
    def _extract_final_answer(self, events: List[Dict]) -> Optional[str]:
        """
        Extract final answer from streaming events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Final answer string or None
        """
        answer_parts = []
        
        for event in events:
            event_type = event.get('event')
            
            if event_type == 'message':
                answer = event.get('answer', '')
                if answer:
                    answer_parts.append(answer)
            elif event_type == 'message_end':
                # Final event, can extract complete answer if needed
                pass
        
        return ''.join(answer_parts) if answer_parts else None
    
    def _extract_metadata(self, events: List[Dict]) -> Dict:
        """
        Extract metadata from streaming events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Dictionary with metadata (usage, timing, etc.)
        """
        metadata = {
            'conversation_id': None,
            'message_id': None,
            'usage': {},
            'files': []
        }
        
        for event in events:
            event_type = event.get('event')
            
            if event_type == 'message':
                if not metadata['conversation_id']:
                    metadata['conversation_id'] = event.get('conversation_id')
                if not metadata['message_id']:
                    metadata['message_id'] = event.get('message_id')
            
            elif event_type == 'message_end':
                event_metadata = event.get('metadata', {})
                metadata['usage'] = event_metadata.get('usage', {})
                metadata['message_id'] = event.get('id')
                metadata['conversation_id'] = event.get('conversation_id')
            
            elif event_type == 'message_file':
                file_info = {
                    'id': event.get('id'),
                    'type': event.get('type'),
                    'url': event.get('url'),
                    'belongs_to': event.get('belongs_to')
                }
                metadata['files'].append(file_info)
        
        return metadata
    
    def send_chat_message(
        self, 
        query: str, 
        user: str = "research_bot",
        conversation_id: Optional[str] = None,
        timeout: int = 120
    ) -> Tuple[Optional[str], Dict, float]:
        """
        Send a chat message to Dify API.
        
        Args:
            query: The query/prompt to send
            user: User identifier
            conversation_id: Optional conversation ID to continue conversation
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (answer, metadata, elapsed_time)
        """
        url = f"{self.base_url}/chat-messages"
        
        payload = {
            "query": query,
            "user": user,
            "response_mode": "streaming",
            "inputs": {}
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        start_time = time.time()
        
        try:
            logger.info(f"Sending query: {query[:100]}...")
            response = requests.post(
                url, 
                headers=self.headers, 
                json=payload,
                timeout=timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Collect all streaming data
            full_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    full_response += line + "\n"
            
            elapsed_time = time.time() - start_time
            
            # Parse events
            events = self._parse_streaming_response(full_response)
            
            # Extract answer and metadata
            answer = self._extract_final_answer(events)
            metadata = self._extract_metadata(events)
            
            logger.info(f"Received response in {elapsed_time:.2f}s")
            
            return answer, metadata, elapsed_time
            
        except requests.exceptions.RequestException as e:
            elapsed_time = time.time() - start_time
            logger.error(f"API request failed: {e}")
            return None, {}, elapsed_time
    
    def generate_campaign_content(
        self, 
        product_type: str, 
        event_type: str,
        user: str = "research_bot",
        timeout: int = 120
    ) -> Tuple[Optional[str], Dict, float]:
        """
        Generate campaign content (text).
        
        Args:
            product_type: Type of product
            event_type: Type of event
            user: User identifier
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (content_json_string, metadata, elapsed_time)
        """
        query = f"Generate advertising campaign for product: {product_type}, event: {event_type}"
        return self.send_chat_message(query, user=user, timeout=timeout)
    
    def generate_campaign_image(
        self,
        image_prompt: str,
        conversation_id: str,
        user: str = "research_bot",
        timeout: int = 120
    ) -> Tuple[Optional[str], Dict, float]:
        """
        Generate campaign image.
        
        Args:
            image_prompt: Prompt for image generation
            conversation_id: Conversation ID to continue
            user: User identifier
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (response, metadata, elapsed_time)
        """
        query = f"Generate a high-quality advertising image based on this description: {image_prompt}"
        return self.send_chat_message(
            query, 
            user=user, 
            conversation_id=conversation_id,
            timeout=timeout
        )
    
    def evaluate_campaign(
        self,
        campaign_data: Dict,
        conversation_id: str,
        user: str = "research_bot",
        timeout: int = 60
    ) -> Tuple[Optional[str], Dict, float]:
        """
        Evaluate a campaign.
        
        Args:
            campaign_data: Campaign data to evaluate
            conversation_id: Conversation ID to continue
            user: User identifier
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (evaluation_json_string, metadata, elapsed_time)
        """
        query = f"Evaluate this advertisement: {json.dumps(campaign_data)}"
        return self.send_chat_message(
            query,
            user=user,
            conversation_id=conversation_id,
            timeout=timeout
        )
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        user: str = "research_bot"
    ) -> Optional[List[Dict]]:
        """
        Get conversation history messages.
        
        Args:
            conversation_id: Conversation ID
            user: User identifier
            
        Returns:
            List of messages or None
        """
        url = f"{self.base_url}/messages"
        params = {
            "conversation_id": conversation_id,
            "user": user,
            "limit": 20
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get messages: {e}")
            return None
