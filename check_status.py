"""
Utility script to check campaign generation status and statistics.
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import func
from datetime import datetime

from database import get_session, Campaign, Evaluation

load_dotenv()


def print_header(text):
    """Print formatted header."""
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)


def check_status():
    """Check current status of campaign generation."""
    session = get_session()
    
    print_header("EVENTAIC RESEARCH - STATUS CHECK")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall statistics
    total = session.query(Campaign).count()
    completed = session.query(Campaign).filter(Campaign.status == 'completed').count()
    generating = session.query(Campaign).filter(Campaign.status == 'generating').count()
    failed = session.query(Campaign).filter(Campaign.status == 'failed').count()
    pending = session.query(Campaign).filter(Campaign.status == 'pending').count()
    
    print(f"\nTotal Campaigns: {total}")
    print(f"  ✓ Completed: {completed} ({completed/total*100 if total > 0 else 0:.1f}%)")
    print(f"  ⏳ Generating: {generating}")
    print(f"  ✗ Failed: {failed}")
    print(f"  ○ Pending: {pending}")
    
    # Completion rate
    if total > 0:
        completion_rate = (completed / total) * 100
        print(f"\nCompletion Rate: {completion_rate:.1f}%")
        
        if completion_rate < 100:
            remaining = total - completed
            print(f"Remaining: {remaining} campaigns")
    
    # Model configuration breakdown
    if completed > 0:
        print("\nBy Model Configuration:")
        configs = session.query(
            Campaign.model_configuration,
            func.count(Campaign.id)
        ).filter(
            Campaign.status == 'completed'
        ).group_by(
            Campaign.model_configuration
        ).all()
        
        for config, count in configs:
            print(f"  - {config.capitalize()}: {count}")
    
    # Average scores
    if completed > 0:
        avg_scores = session.query(
            func.avg(Evaluation.overall_score).label('overall'),
            func.avg(Evaluation.relevance_score).label('relevance'),
            func.avg(Evaluation.clarity_score).label('clarity'),
            func.avg(Evaluation.persuasiveness_score).label('persuasiveness'),
            func.avg(Evaluation.brand_safety_score).label('brand_safety')
        ).join(Campaign).filter(Campaign.status == 'completed').first()
        
        if avg_scores.overall:
            print("\nAverage Quality Scores:")
            print(f"  Overall: {avg_scores.overall:.2f}/10")
            print(f"  Relevance: {avg_scores.relevance:.2f}/10")
            print(f"  Clarity: {avg_scores.clarity:.2f}/10")
            print(f"  Persuasiveness: {avg_scores.persuasiveness:.2f}/10")
            print(f"  Brand Safety: {avg_scores.brand_safety:.2f}/10")
    
    # Recent failures
    if failed > 0:
        print("\nRecent Failed Campaigns:")
        failed_campaigns = session.query(Campaign).filter(
            Campaign.status == 'failed'
        ).order_by(Campaign.campaign_number).limit(5).all()
        
        for campaign in failed_campaigns:
            print(f"  - Campaign #{campaign.campaign_number}: {campaign.product_type} x {campaign.event_type}")
    
    # Time estimates
    if completed > 0:
        from sqlalchemy import and_
        avg_time = session.query(
            func.avg(Campaign.completed_at - Campaign.started_at)
        ).filter(
            and_(
                Campaign.status == 'completed',
                Campaign.started_at.isnot(None),
                Campaign.completed_at.isnot(None)
            )
        ).scalar()
        
        if avg_time and remaining > 0:
            estimated_remaining_seconds = avg_time.total_seconds() * remaining
            estimated_hours = estimated_remaining_seconds / 3600
            print(f"\nEstimated Time Remaining: {estimated_hours:.1f} hours")
    
    print("\n" + "="*60 + "\n")
    
    session.close()


def show_failed_details():
    """Show detailed information about failed campaigns."""
    session = get_session()
    
    failed_campaigns = session.query(Campaign).filter(
        Campaign.status == 'failed'
    ).all()
    
    if not failed_campaigns:
        print("No failed campaigns found.")
        return
    
    print_header("FAILED CAMPAIGNS DETAILS")
    
    for campaign in failed_campaigns:
        print(f"\nCampaign #{campaign.campaign_number}")
        print(f"  Product: {campaign.product_type}")
        print(f"  Event: {campaign.event_type}")
        print(f"  Configuration: {campaign.model_configuration}")
        print(f"  Started: {campaign.started_at}")
        
        # Check what stages were completed
        has_text = campaign.text_content is not None
        has_image = len(campaign.images) > 0
        has_eval = campaign.evaluation is not None
        
        print(f"  Stages completed:")
        print(f"    - Text: {'✓' if has_text else '✗'}")
        print(f"    - Image: {'✓' if has_image else '✗'}")
        print(f"    - Evaluation: {'✓' if has_eval else '✗'}")
    
    print("\n" + "="*60 + "\n")
    session.close()


def show_product_breakdown():
    """Show performance breakdown by product type."""
    session = get_session()
    
    print_header("PERFORMANCE BY PRODUCT TYPE")
    
    results = session.query(
        Campaign.product_type,
        func.count(Campaign.id).label('total'),
        func.avg(Evaluation.overall_score).label('avg_score')
    ).join(
        Evaluation, Campaign.id == Evaluation.campaign_id, isouter=True
    ).filter(
        Campaign.status == 'completed'
    ).group_by(
        Campaign.product_type
    ).order_by(
        func.avg(Evaluation.overall_score).desc()
    ).all()
    
    if results:
        print(f"\n{'Product':<20} {'Count':<10} {'Avg Score':<10}")
        print("-" * 60)
        for product, count, score in results:
            score_str = f"{score:.2f}" if score else "N/A"
            print(f"{product:<20} {count:<10} {score_str:<10}")
    else:
        print("\nNo completed campaigns with evaluations found.")
    
    print("\n" + "="*60 + "\n")
    session.close()


def main():
    """Main function."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'failed':
            show_failed_details()
        elif command == 'products':
            show_product_breakdown()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: failed, products")
    else:
        check_status()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
