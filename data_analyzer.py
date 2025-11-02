"""
Data analyzer for generating research statistics and visualizations.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from typing import Dict, List
import logging
from pathlib import Path

from database import get_session, Campaign

logger = logging.getLogger(__name__)

# Set visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


class DataAnalyzer:
    """Analyzes campaign data and generates research statistics."""
    
    def __init__(self, output_dir: str = "analysis_results"):
        """
        Initialize data analyzer.
        
        Args:
            output_dir: Directory to save analysis results
        """
        self.session = get_session()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def load_campaign_data(self) -> pd.DataFrame:
        """
        Load all campaign data into a pandas DataFrame.
        
        Returns:
            DataFrame with all campaign data
        """
        logger.info("Loading campaign data from database")
        
        # Query all campaigns with related data
        campaigns = self.session.query(Campaign).filter(
            Campaign.status == 'completed'
        ).all()
        
        data = []
        for campaign in campaigns:
            row = {
                'campaign_number': campaign.campaign_number,
                'product_type': campaign.product_type,
                'event_type': campaign.event_type,
                'model_configuration': campaign.model_configuration,
                
                # Text content
                'headline': campaign.text_content.headline if campaign.text_content else None,
                'description': campaign.text_content.description if campaign.text_content else None,
                'cta': campaign.text_content.cta if campaign.text_content else None,
                
                # Evaluation scores
                'relevance_score': campaign.evaluation.relevance_score if campaign.evaluation else None,
                'clarity_score': campaign.evaluation.clarity_score if campaign.evaluation else None,
                'persuasiveness_score': campaign.evaluation.persuasiveness_score if campaign.evaluation else None,
                'brand_safety_score': campaign.evaluation.brand_safety_score if campaign.evaluation else None,
                'overall_score': campaign.evaluation.overall_score if campaign.evaluation else None,
                
                # Timing metrics
                'text_generation_time': campaign.timings.text_generation_time if campaign.timings else None,
                'image_generation_time': campaign.timings.image_generation_time if campaign.timings else None,
                'evaluation_time': campaign.timings.evaluation_time if campaign.timings else None,
                'total_time': campaign.timings.total_time if campaign.timings else None,
                
                # Cost metrics
                'total_cost': campaign.costs.total_cost if campaign.costs else None,
                'total_tokens': campaign.costs.total_tokens if campaign.costs else None,
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} campaigns")
        
        return df
    
    def generate_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics for the research paper.
        
        Args:
            df: DataFrame with campaign data
            
        Returns:
            Dictionary with summary statistics
        """
        logger.info("Generating summary statistics")
        
        stats_dict = {
            'total_campaigns': len(df),
            
            # Generation time statistics
            'mean_text_generation_time': df['text_generation_time'].mean(),
            'std_text_generation_time': df['text_generation_time'].std(),
            'mean_image_generation_time': df['image_generation_time'].mean(),
            'std_image_generation_time': df['image_generation_time'].std(),
            'mean_evaluation_time': df['evaluation_time'].mean(),
            'std_evaluation_time': df['evaluation_time'].std(),
            'mean_total_time': df['total_time'].mean(),
            'std_total_time': df['total_time'].std(),
            
            # Quality score statistics
            'mean_relevance_score': df['relevance_score'].mean(),
            'std_relevance_score': df['relevance_score'].std(),
            'mean_clarity_score': df['clarity_score'].mean(),
            'std_clarity_score': df['clarity_score'].std(),
            'mean_persuasiveness_score': df['persuasiveness_score'].mean(),
            'std_persuasiveness_score': df['persuasiveness_score'].std(),
            'mean_brand_safety_score': df['brand_safety_score'].mean(),
            'std_brand_safety_score': df['brand_safety_score'].std(),
            'mean_overall_score': df['overall_score'].mean(),
            'std_overall_score': df['overall_score'].std(),
            
            # Cost statistics
            'mean_total_cost': df['total_cost'].mean(),
            'std_total_cost': df['total_cost'].std(),
            'total_cost_all_campaigns': df['total_cost'].sum(),
            
            # By model configuration
            'by_model_config': {}
        }
        
        # Statistics by model configuration
        for config in df['model_configuration'].unique():
            config_df = df[df['model_configuration'] == config]
            stats_dict['by_model_config'][config] = {
                'count': len(config_df),
                'mean_time': config_df['total_time'].mean(),
                'mean_score': config_df['overall_score'].mean(),
                'mean_cost': config_df['total_cost'].mean()
            }
        
        # By product type
        stats_dict['by_product_type'] = {}
        for product in df['product_type'].unique():
            product_df = df[df['product_type'] == product]
            stats_dict['by_product_type'][product] = {
                'count': len(product_df),
                'mean_score': product_df['overall_score'].mean()
            }
        
        return stats_dict
    
    def generate_statistical_tests(self, df: pd.DataFrame) -> Dict:
        """
        Perform statistical tests for research paper.
        
        Args:
            df: DataFrame with campaign data
            
        Returns:
            Dictionary with test results
        """
        logger.info("Performing statistical tests")
        
        tests = {}
        
        # ANOVA: Compare model configurations
        configs = df['model_configuration'].unique()
        if len(configs) >= 2:
            groups = [df[df['model_configuration'] == c]['overall_score'].dropna() 
                     for c in configs]
            if all(len(g) > 0 for g in groups):
                f_stat, p_value = stats.f_oneway(*groups)
                tests['anova_model_config'] = {
                    'f_statistic': f_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05
                }
        
        # Correlation: Generation time vs quality
        if df['total_time'].notna().any() and df['overall_score'].notna().any():
            corr, p_value = stats.pearsonr(
                df['total_time'].dropna(),
                df['overall_score'].dropna()
            )
            tests['correlation_time_quality'] = {
                'correlation': corr,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
        
        # T-test: Compare speed vs quality configurations
        if 'speed' in configs and 'quality' in configs:
            speed_scores = df[df['model_configuration'] == 'speed']['overall_score'].dropna()
            quality_scores = df[df['model_configuration'] == 'quality']['overall_score'].dropna()
            
            if len(speed_scores) > 0 and len(quality_scores) > 0:
                t_stat, p_value = stats.ttest_ind(speed_scores, quality_scores)
                tests['ttest_speed_vs_quality'] = {
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05,
                    'speed_mean': speed_scores.mean(),
                    'quality_mean': quality_scores.mean()
                }
        
        return tests
    
    def create_visualizations(self, df: pd.DataFrame):
        """
        Create visualizations for research paper.
        
        Args:
            df: DataFrame with campaign data
        """
        logger.info("Creating visualizations")
        
        # 1. Generation time by configuration
        plt.figure(figsize=(10, 6))
        df.boxplot(column='total_time', by='model_configuration')
        plt.title('Generation Time by Model Configuration')
        plt.xlabel('Model Configuration')
        plt.ylabel('Total Time (seconds)')
        plt.suptitle('')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'generation_time_by_config.png', dpi=300)
        plt.close()
        
        # 2. Quality scores distribution
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        df['relevance_score'].hist(ax=axes[0, 0], bins=20, edgecolor='black')
        axes[0, 0].set_title('Relevance Score Distribution')
        axes[0, 0].set_xlabel('Score')
        
        df['clarity_score'].hist(ax=axes[0, 1], bins=20, edgecolor='black')
        axes[0, 1].set_title('Clarity Score Distribution')
        axes[0, 1].set_xlabel('Score')
        
        df['persuasiveness_score'].hist(ax=axes[1, 0], bins=20, edgecolor='black')
        axes[1, 0].set_title('Persuasiveness Score Distribution')
        axes[1, 0].set_xlabel('Score')
        
        df['brand_safety_score'].hist(ax=axes[1, 1], bins=20, edgecolor='black')
        axes[1, 1].set_title('Brand Safety Score Distribution')
        axes[1, 1].set_xlabel('Score')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'quality_scores_distribution.png', dpi=300)
        plt.close()
        
        # 3. Mean scores by product category
        plt.figure(figsize=(12, 6))
        product_scores = df.groupby('product_type')['overall_score'].mean().sort_values(ascending=False)
        product_scores.plot(kind='bar')
        plt.title('Mean Overall Score by Product Category')
        plt.xlabel('Product Type')
        plt.ylabel('Mean Overall Score')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'scores_by_product.png', dpi=300)
        plt.close()
        
        # 4. Cost vs Quality scatter plot
        plt.figure(figsize=(10, 6))
        plt.scatter(df['total_cost'], df['overall_score'], alpha=0.6)
        plt.xlabel('Total Cost ($)')
        plt.ylabel('Overall Score')
        plt.title('Cost vs Quality Trade-off')
        
        # Add regression line
        z = np.polyfit(df['total_cost'].dropna(), df['overall_score'].dropna(), 1)
        p = np.poly1d(z)
        plt.plot(df['total_cost'].sort_values(), p(df['total_cost'].sort_values()), 
                "r--", alpha=0.8, label=f'Trend line')
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.output_dir / 'cost_vs_quality.png', dpi=300)
        plt.close()
        
        # 5. Heatmap of scores by product and event
        pivot_relevance = df.pivot_table(
            values='overall_score', 
            index='product_type', 
            columns='event_type',
            aggfunc='mean'
        )
        
        plt.figure(figsize=(14, 10))
        sns.heatmap(pivot_relevance, annot=True, fmt='.2f', cmap='YlOrRd')
        plt.title('Mean Overall Score by Product Type and Event Type')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'heatmap_product_event.png', dpi=300)
        plt.close()
        
        logger.info(f"Visualizations saved to {self.output_dir}")
    
    def generate_latex_tables(self, df: pd.DataFrame, stats: Dict):
        """
        Generate LaTeX tables for research paper.
        
        Args:
            df: DataFrame with campaign data
            stats: Statistics dictionary
        """
        logger.info("Generating LaTeX tables")
        
        # Table 1: Summary Statistics
        table1 = """
\\begin{table}[h]
\\centering
\\caption{Summary Statistics of Campaign Generation}
\\label{tab:summary_stats}
\\begin{tabular}{lcc}
\\hline
\\textbf{Metric} & \\textbf{Mean} & \\textbf{Std. Dev.} \\\\
\\hline
Text Generation Time (s) & {:.2f} & {:.2f} \\\\
Image Generation Time (s) & {:.2f} & {:.2f} \\\\
Evaluation Time (s) & {:.2f} & {:.2f} \\\\
Total Generation Time (s) & {:.2f} & {:.2f} \\\\
\\hline
Relevance Score & {:.2f} & {:.2f} \\\\
Clarity Score & {:.2f} & {:.2f} \\\\
Persuasiveness Score & {:.2f} & {:.2f} \\\\
Brand Safety Score & {:.2f} & {:.2f} \\\\
Overall Score & {:.2f} & {:.2f} \\\\
\\hline
Total Cost (\\$) & {:.4f} & {:.4f} \\\\
\\hline
\\end{tabular}
\\end{table}
""".format(
            stats['mean_text_generation_time'], stats['std_text_generation_time'],
            stats['mean_image_generation_time'], stats['std_image_generation_time'],
            stats['mean_evaluation_time'], stats['std_evaluation_time'],
            stats['mean_total_time'], stats['std_total_time'],
            stats['mean_relevance_score'], stats['std_relevance_score'],
            stats['mean_clarity_score'], stats['std_clarity_score'],
            stats['mean_persuasiveness_score'], stats['std_persuasiveness_score'],
            stats['mean_brand_safety_score'], stats['std_brand_safety_score'],
            stats['mean_overall_score'], stats['std_overall_score'],
            stats['mean_total_cost'], stats['std_total_cost']
        )
        
        with open(self.output_dir / 'table_summary_stats.tex', 'w') as f:
            f.write(table1)
        
        # Table 2: Performance by Model Configuration
        config_data = []
        for config, data in stats['by_model_config'].items():
            config_data.append([
                config.capitalize(),
                data['count'],
                f"{data['mean_time']:.2f}",
                f"{data['mean_score']:.2f}",
                f"{data['mean_cost']:.4f}"
            ])
        
        table2 = """
\\begin{table}[h]
\\centering
\\caption{Performance by Model Configuration}
\\label{tab:model_config}
\\begin{tabular}{lcccc}
\\hline
\\textbf{Configuration} & \\textbf{Count} & \\textbf{Mean Time (s)} & \\textbf{Mean Score} & \\textbf{Mean Cost (\\$)} \\\\
\\hline
"""
        for row in config_data:
            table2 += " & ".join(str(x) for x in row) + " \\\\\n"
        
        table2 += """\\hline
\\end{tabular}
\\end{table}
"""
        
        with open(self.output_dir / 'table_model_config.tex', 'w') as f:
            f.write(table2)
        
        logger.info(f"LaTeX tables saved to {self.output_dir}")
    
    def generate_full_report(self) -> Dict:
        """
        Generate complete analysis report.
        
        Returns:
            Dictionary with all analysis results
        """
        logger.info("Generating full analysis report")
        
        # Load data
        df = self.load_campaign_data()
        
        if len(df) == 0:
            logger.warning("No completed campaigns found")
            return {}
        
        # Generate statistics
        stats = self.generate_summary_statistics(df)
        
        # Perform statistical tests
        tests = self.generate_statistical_tests(df)
        
        # Create visualizations
        self.create_visualizations(df)
        
        # Generate LaTeX tables
        self.generate_latex_tables(df, stats)
        
        # Save data to CSV
        df.to_csv(self.output_dir / 'campaign_data.csv', index=False)
        
        # Save statistics to JSON
        import json
        with open(self.output_dir / 'statistics.json', 'w') as f:
            json.dump({
                'summary_statistics': stats,
                'statistical_tests': tests
            }, f, indent=2, default=str)
        
        logger.info("Analysis report completed")
        
        return {
            'data': df,
            'statistics': stats,
            'tests': tests
        }
    
    def __del__(self):
        """Cleanup session on deletion."""
        if hasattr(self, 'session'):
            self.session.close()
