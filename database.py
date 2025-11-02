"""
Database models for EventAIC research data collection.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, 
    DateTime, Text, JSON, ForeignKey, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class Campaign(Base):
    """Main campaign table storing all campaign metadata."""
    __tablename__ = 'campaigns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_number = Column(Integer, unique=True, nullable=False, index=True)
    product_type = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=False)
    
    # Configuration
    model_configuration = Column(String(50), nullable=False)  # speed, balanced, quality
    
    # Dify conversation tracking
    conversation_id = Column(String(255), unique=True)
    
    # Status tracking
    status = Column(String(50), default='pending')  # pending, generating, evaluating, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    text_content = relationship("TextContent", back_populates="campaign", uselist=False)
    images = relationship("ImageGeneration", back_populates="campaign")
    evaluation = relationship("Evaluation", back_populates="campaign", uselist=False)
    timings = relationship("TimingMetrics", back_populates="campaign", uselist=False)
    costs = relationship("CostMetrics", back_populates="campaign", uselist=False)


class TextContent(Base):
    """Stores generated text content for campaigns."""
    __tablename__ = 'text_content'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), unique=True, nullable=False)
    
    # Generated content
    headline = Column(String(500))
    description = Column(Text)
    cta = Column(String(200))
    keywords = Column(JSON)  # Array of keywords
    
    # Metadata
    message_id = Column(String(255), unique=True)
    raw_response = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="text_content")


class ImageGeneration(Base):
    """Stores generated images and their metadata."""
    __tablename__ = 'images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    
    # Image data
    image_url = Column(String(500))
    image_prompt = Column(Text)
    model_used = Column(String(100))
    
    # Image specifications
    width = Column(Integer)
    height = Column(Integer)
    steps = Column(Integer)
    seed = Column(Integer)
    
    # Metadata
    message_id = Column(String(255))
    file_id = Column(String(255))
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="images")


class Evaluation(Base):
    """Stores evaluation scores for campaigns."""
    __tablename__ = 'evaluations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), unique=True, nullable=False)
    
    # Core evaluation scores (0-10)
    relevance_score = Column(Float)
    clarity_score = Column(Float)
    persuasiveness_score = Column(Float)
    brand_safety_score = Column(Float)
    overall_score = Column(Float)
    
    # Detailed evaluation
    feedback = Column(Text)
    recommendations = Column(JSON)  # Array of recommendations
    
    # Metadata
    message_id = Column(String(255))
    raw_response = Column(JSON)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="evaluation")


class TimingMetrics(Base):
    """Stores timing metrics for each campaign generation stage."""
    __tablename__ = 'timing_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), unique=True, nullable=False)
    
    # Stage timings (in seconds)
    text_generation_time = Column(Float)
    image_generation_time = Column(Float)
    evaluation_time = Column(Float)
    total_time = Column(Float)
    
    # Additional metrics
    text_tokens_used = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="timings")


class CostMetrics(Base):
    """Stores cost metrics for each campaign."""
    __tablename__ = 'cost_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), unique=True, nullable=False)
    
    # Cost breakdown
    text_generation_cost = Column(Float, default=0.0)
    image_generation_cost = Column(Float, default=0.0)
    evaluation_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    currency = Column(String(10), default='USD')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="costs")


# Database connection helper
def get_database_url():
    """Construct database URL from environment variables."""
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'eventaic_research')
    user = os.getenv('POSTGRES_USER', 'eventaic_user')
    password = os.getenv('POSTGRES_PASSWORD', '')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def create_database_engine():
    """Create and return SQLAlchemy engine."""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)
    return engine


def init_database():
    """Initialize database schema."""
    engine = create_database_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get database session."""
    engine = create_database_engine()
    Session = sessionmaker(bind=engine)
    return Session()
