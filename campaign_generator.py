"""
Campaign generator for EventAIC research data collection.
"""
import json
import time
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from tqdm import tqdm

from dify_client import DifyAPIClient
from database import (
    get_session, Campaign, TextContent, ImageGeneration,
    Evaluation, TimingMetrics, CostMetrics
)

logger = logging.getLogger(__name__)


class CampaignGenerator:
    """Orchestrates campaign generation, image creation, and evaluation."""
    
    # Product types and event types for the experiment
    PRODUCT_TYPES = [
        "Smartphone",
        "Laptop",
        "Smartwatch",
        "Headphones",
        "Tablet",
        "Gaming Console",
        "Camera",
        "Fitness Tracker",
        "E-reader",
        "Smart Home Device"
    ]
    
    EVENT_TYPES = [
        "Black Friday",
        "Christmas",
        "New Year",
        "Valentine's Day",
        "Mother's Day",
        "Back to School",
        "Summer Sale",
        "Cyber Monday",
        "Father's Day",
        "Halloween"
    ]
    
    MODEL_CONFIGS = {
        'speed': {
            'name': 'speed',
            'description': 'Fast generation with FLUX.1 Schnell',
            'steps': 4
        },
        'balanced': {
            'name': 'balanced',
            'description': 'Balanced quality and speed',
            'steps': 20
        },
        'quality': {
            'name': 'quality',
            'description': 'High quality with FLUX.1 Pro',
            'steps': 50
        }
    }
    
    def __init__(self, dify_client: DifyAPIClient, batch_size: int = 10):
        """
        Initialize campaign generator.
        
        Args:
            dify_client: Dify API client instance
            batch_size: Number of campaigns to generate before committing to DB
        """
        self.dify_client = dify_client
        self.batch_size = batch_size
        self.session = get_session()
    
    def _get_model_config(self, campaign_number: int) -> str:
        """
        Determine model configuration based on campaign number.
        Distribute evenly across speed, balanced, and quality.
        
        Args:
            campaign_number: Campaign number (1-100)
            
        Returns:
            Model configuration name
        """
        configs = list(self.MODEL_CONFIGS.keys())
        index = (campaign_number - 1) % len(configs)
        return configs[index]
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON response from LLM, handling various formats.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed JSON dictionary or None
        """
        if not response_text:
            return None
        
        # Try direct JSON parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        if '```json' in response_text:
            try:
                start = response_text.index('```json') + 7
                end = response_text.index('```', start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass
        
        # Try to extract JSON from plain code blocks
        if '```' in response_text:
            try:
                start = response_text.index('```') + 3
                end = response_text.index('```', start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass
        
        logger.warning("Failed to parse JSON response")
        return None
    
    def generate_campaign(
        self, 
        campaign_number: int,
        product_type: str,
        event_type: str
    ) -> bool:
        """
        Generate a complete campaign with text, image, and evaluation.
        
        Args:
            campaign_number: Campaign number (1-100)
            product_type: Type of product
            event_type: Type of event
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting campaign {campaign_number}: {product_type} x {event_type}")
        
        # Create campaign record
        model_config = self._get_model_config(campaign_number)
        campaign = Campaign(
            campaign_number=campaign_number,
            product_type=product_type,
            event_type=event_type,
            model_configuration=model_config,
            status='generating',
            started_at=datetime.utcnow()
        )
        
        try:
            self.session.add(campaign)
            self.session.commit()
            
            # Step 1: Generate text content
            text_success = self._generate_text_content(campaign)
            if not text_success:
                campaign.status = 'failed'
                self.session.commit()
                return False
            
            # Step 2: Generate image
            image_success = self._generate_image(campaign)
            if not image_success:
                logger.warning(f"Image generation failed for campaign {campaign_number}")
                # Continue anyway - we still have text
            
            # Step 3: Evaluate campaign
            eval_success = self._evaluate_campaign(campaign)
            if not eval_success:
                logger.warning(f"Evaluation failed for campaign {campaign_number}")
            
            # Mark as completed
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
            
            # Calculate total time
            if campaign.timings:
                total = (
                    (campaign.timings.text_generation_time or 0) +
                    (campaign.timings.image_generation_time or 0) +
                    (campaign.timings.evaluation_time or 0)
                )
                campaign.timings.total_time = total
            
            self.session.commit()
            
            logger.info(f"Campaign {campaign_number} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Campaign {campaign_number} failed: {e}", exc_info=True)
            campaign.status = 'failed'
            self.session.commit()
            return False
    
    def _generate_text_content(self, campaign: Campaign) -> bool:
        """Generate text content for campaign."""
        logger.info(f"Generating text content for campaign {campaign.campaign_number}")
        
        # Generate content
        response, metadata, elapsed_time = self.dify_client.generate_campaign_content(
            product_type=campaign.product_type,
            event_type=campaign.event_type,
            timeout=120
        )
        
        if not response:
            logger.error("Text generation failed - no response")
            return False
        
        # Parse JSON response
        content_data = self._parse_json_response(response)
        if not content_data:
            logger.error("Failed to parse text content JSON")
            return False
        
        # Store conversation ID for later use
        campaign.conversation_id = metadata.get('conversation_id')
        
        # Create text content record
        text_content = TextContent(
            campaign_id=campaign.id,
            headline=content_data.get('headline'),
            description=content_data.get('description'),
            cta=content_data.get('cta'),
            keywords=content_data.get('keywords', []),
            message_id=metadata.get('message_id'),
            raw_response=content_data
        )
        
        # Create timing record
        timing = TimingMetrics(
            campaign_id=campaign.id,
            text_generation_time=elapsed_time
        )
        
        # Create cost record
        usage = metadata.get('usage', {})
        cost = CostMetrics(
            campaign_id=campaign.id,
            text_generation_cost=float(usage.get('total_price', 0)),
            prompt_tokens=int(usage.get('prompt_tokens', 0)),
            completion_tokens=int(usage.get('completion_tokens', 0)),
            total_tokens=int(usage.get('total_tokens', 0)),
            currency=usage.get('currency', 'USD')
        )
        
        self.session.add(text_content)
        self.session.add(timing)
        self.session.add(cost)
        self.session.commit()
        
        logger.info(f"Text content generated in {elapsed_time:.2f}s")
        return True
    
    def _generate_image(self, campaign: Campaign) -> bool:
        """Generate image for campaign."""
        logger.info(f"Generating image for campaign {campaign.campaign_number}")
        
        if not campaign.conversation_id:
            logger.error("No conversation ID available for image generation")
            return False
        
        # Get text content to create image prompt
        text_content = campaign.text_content
        if not text_content:
            logger.error("No text content available for image generation")
            return False
        
        # Create image prompt from headline and description
        image_prompt = f"{text_content.headline}. {text_content.description[:200]}"
        
        # Generate image
        response, metadata, elapsed_time = self.dify_client.generate_campaign_image(
            image_prompt=image_prompt,
            conversation_id=campaign.conversation_id,
            timeout=120
        )
        
        # Extract image file from metadata
        files = metadata.get('files', [])
        if not files:
            logger.error("No image files in response")
            return False
        
        image_file = files[0]  # Take first image
        
        # Create image record
        image = ImageGeneration(
            campaign_id=campaign.id,
            image_url=image_file.get('url'),
            image_prompt=image_prompt,
            model_used=campaign.model_configuration,
            width=1024,
            height=1024,
            steps=self.MODEL_CONFIGS[campaign.model_configuration]['steps'],
            message_id=metadata.get('message_id'),
            file_id=image_file.get('id')
        )
        
        # Update timing
        if campaign.timings:
            campaign.timings.image_generation_time = elapsed_time
        
        # Update cost
        if campaign.costs:
            usage = metadata.get('usage', {})
            campaign.costs.image_generation_cost = float(usage.get('total_price', 0))
        
        self.session.add(image)
        self.session.commit()
        
        logger.info(f"Image generated in {elapsed_time:.2f}s")
        return True
    
    def _evaluate_campaign(self, campaign: Campaign) -> bool:
        """Evaluate campaign."""
        logger.info(f"Evaluating campaign {campaign.campaign_number}")
        
        if not campaign.conversation_id:
            logger.error("No conversation ID available for evaluation")
            return False
        
        # Prepare campaign data for evaluation
        text_content = campaign.text_content
        campaign_data = {
            "product": campaign.product_type,
            "event": campaign.event_type,
            "headline": text_content.headline if text_content else "",
            "description": text_content.description if text_content else "",
            "cta": text_content.cta if text_content else ""
        }
        
        # Evaluate
        response, metadata, elapsed_time = self.dify_client.evaluate_campaign(
            campaign_data=campaign_data,
            conversation_id=campaign.conversation_id,
            timeout=60
        )
        
        if not response:
            logger.error("Evaluation failed - no response")
            return False
        
        # Parse evaluation JSON
        eval_data = self._parse_json_response(response)
        if not eval_data:
            logger.error("Failed to parse evaluation JSON")
            return False
        
        # Create evaluation record
        evaluation = Evaluation(
            campaign_id=campaign.id,
            relevance_score=float(eval_data.get('relevance', 0)),
            clarity_score=float(eval_data.get('clarity', 0)),
            persuasiveness_score=float(eval_data.get('persuasiveness', 0)),
            brand_safety_score=float(eval_data.get('brand_safety', 0)),
            overall_score=float(eval_data.get('overall_score', 0)),
            feedback=eval_data.get('feedback', ''),
            recommendations=eval_data.get('recommendations', []),
            message_id=metadata.get('message_id'),
            raw_response=eval_data
        )
        
        # Update timing
        if campaign.timings:
            campaign.timings.evaluation_time = elapsed_time
        
        # Update cost
        if campaign.costs:
            usage = metadata.get('usage', {})
            campaign.costs.evaluation_cost = float(usage.get('total_price', 0))
            campaign.costs.total_cost = (
                campaign.costs.text_generation_cost +
                campaign.costs.image_generation_cost +
                campaign.costs.evaluation_cost
            )
        
        self.session.add(evaluation)
        self.session.commit()
        
        logger.info(f"Evaluation completed in {elapsed_time:.2f}s")
        return True
    
    def generate_all_campaigns(self, total_campaigns: int = 100) -> Dict:
        """
        Generate all campaigns for the research.
        
        Args:
            total_campaigns: Total number of campaigns to generate
            
        Returns:
            Summary statistics dictionary
        """
        logger.info(f"Starting generation of {total_campaigns} campaigns")
        
        successful = 0
        failed = 0
        
        # Create campaign combinations
        campaigns_to_generate = []
        for i in range(total_campaigns):
            product_idx = i % len(self.PRODUCT_TYPES)
            event_idx = (i // len(self.PRODUCT_TYPES)) % len(self.EVENT_TYPES)
            
            campaigns_to_generate.append({
                'number': i + 1,
                'product': self.PRODUCT_TYPES[product_idx],
                'event': self.EVENT_TYPES[event_idx]
            })
        
        # Generate campaigns with progress bar
        for campaign_info in tqdm(campaigns_to_generate, desc="Generating campaigns"):
            success = self.generate_campaign(
                campaign_number=campaign_info['number'],
                product_type=campaign_info['product'],
                event_type=campaign_info['event']
            )
            
            if success:
                successful += 1
            else:
                failed += 1
            
            # Small delay to avoid overwhelming the API
            time.sleep(1)
        
        summary = {
            'total': total_campaigns,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total_campaigns * 100) if total_campaigns > 0 else 0
        }
        
        logger.info(f"Campaign generation completed: {successful}/{total_campaigns} successful")
        return summary
    
    def __del__(self):
        """Cleanup session on deletion."""
        if hasattr(self, 'session'):
            self.session.close()
