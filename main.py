"""
Main script for EventAIC research data collection.
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

from database import init_database
from dify_client import DifyAPIClient
from campaign_generator import CampaignGenerator
from data_analyzer import DataAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eventaic_research.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def setup_environment():
    """Load environment variables and validate configuration."""
    load_dotenv()
    
    # Validate required environment variables
    required_vars = [
        'DIFY_API_BASE_URL',
        'DIFY_API_KEY',
        'POSTGRES_HOST',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please create a .env file based on .env.example")
        sys.exit(1)
    
    logger.info("Environment variables loaded successfully")


def generate_campaigns(total_campaigns: int):
    """
    Generate all campaigns.
    
    Args:
        total_campaigns: Number of campaigns to generate
    """
    logger.info(f"Starting campaign generation phase ({total_campaigns} campaigns)")
    
    # Initialize Dify client
    dify_client = DifyAPIClient(
        base_url=os.getenv('DIFY_API_BASE_URL'),
        api_key=os.getenv('DIFY_API_KEY'),
        polling_interval=int(os.getenv('POLLING_INTERVAL', 2))
    )
    
    # Initialize campaign generator
    generator = CampaignGenerator(dify_client)
    
    # Generate campaigns
    summary = generator.generate_all_campaigns(total_campaigns)
    
    logger.info("Campaign generation completed")
    logger.info(f"Summary: {summary}")
    
    return summary


def analyze_data():
    """Analyze generated data and create reports."""
    logger.info("Starting data analysis phase")
    
    # Initialize analyzer
    analyzer = DataAnalyzer(output_dir='analysis_results')
    
    # Generate full report
    results = analyzer.generate_full_report()
    
    if results:
        logger.info("Data analysis completed successfully")
        logger.info(f"Results saved to analysis_results/")
        
        # Print summary
        stats = results.get('statistics', {})
        print("\n" + "="*60)
        print("RESEARCH SUMMARY STATISTICS")
        print("="*60)
        print(f"Total Campaigns: {stats.get('total_campaigns', 0)}")
        print(f"\nGeneration Times:")
        print(f"  - Mean Total Time: {stats.get('mean_total_time', 0):.2f}s")
        print(f"  - Text Generation: {stats.get('mean_text_generation_time', 0):.2f}s")
        print(f"  - Image Generation: {stats.get('mean_image_generation_time', 0):.2f}s")
        print(f"  - Evaluation: {stats.get('mean_evaluation_time', 0):.2f}s")
        print(f"\nQuality Scores (Mean ± SD):")
        print(f"  - Overall: {stats.get('mean_overall_score', 0):.2f} ± {stats.get('std_overall_score', 0):.2f}")
        print(f"  - Relevance: {stats.get('mean_relevance_score', 0):.2f} ± {stats.get('std_relevance_score', 0):.2f}")
        print(f"  - Clarity: {stats.get('mean_clarity_score', 0):.2f} ± {stats.get('std_clarity_score', 0):.2f}")
        print(f"  - Persuasiveness: {stats.get('mean_persuasiveness_score', 0):.2f} ± {stats.get('std_persuasiveness_score', 0):.2f}")
        print(f"  - Brand Safety: {stats.get('mean_brand_safety_score', 0):.2f} ± {stats.get('std_brand_safety_score', 0):.2f}")
        print(f"\nCost Analysis:")
        print(f"  - Mean Cost per Campaign: ${stats.get('mean_total_cost', 0):.4f}")
        print(f"  - Total Cost (All Campaigns): ${stats.get('total_cost_all_campaigns', 0):.4f}")
        print("="*60 + "\n")
    else:
        logger.warning("No data to analyze - generate campaigns first")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='EventAIC Research Data Collection System'
    )
    parser.add_argument(
        '--mode',
        choices=['generate', 'analyze', 'all'],
        default='all',
        help='Operation mode: generate campaigns, analyze data, or both'
    )
    parser.add_argument(
        '--campaigns',
        type=int,
        default=None,
        help='Number of campaigns to generate (default: from .env)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database schema'
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_environment()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database schema...")
        init_database()
        logger.info("Database initialized successfully")
        return
    
    # Determine number of campaigns
    total_campaigns = args.campaigns or int(os.getenv('TOTAL_CAMPAIGNS', 100))
    
    # Execute based on mode
    if args.mode in ['generate', 'all']:
        # Initialize database
        init_database()
        
        # Generate campaigns
        generate_campaigns(total_campaigns)
    
    if args.mode in ['analyze', 'all']:
        # Analyze data
        analyze_data()
    
    logger.info("Process completed successfully")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
