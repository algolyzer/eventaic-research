# EventAIC Research Data Collection System

A comprehensive system for collecting experimental data for the EventAIC research paper on automated advertising campaign generation using AI.

## Overview

This system automates the process of:
1. **Generating 100 advertising campaigns** (10 products × 10 events)
2. **Creating text content** using LLMs (headlines, descriptions, CTAs)
3. **Generating images** using FLUX.1 diffusion models
4. **Evaluating campaigns** across multiple quality dimensions
5. **Collecting timing and cost metrics** for all stages
6. **Analyzing results** with statistical tests and visualizations
7. **Generating research outputs** (tables, figures, LaTeX)

## System Architecture

```
┌─────────────────┐
│  Main Script    │
│   (main.py)     │
└────────┬────────┘
         │
         ├──► Database Setup (database.py)
         │    └─► PostgreSQL with SQLAlchemy
         │
         ├──► Campaign Generation (campaign_generator.py)
         │    ├─► Text Content Generation
         │    ├─► Image Generation (FLUX.1)
         │    └─► Campaign Evaluation
         │
         ├──► Dify API Client (dify_client.py)
         │    └─► Handles API communication
         │
         └──► Data Analysis (data_analyzer.py)
              ├─► Statistical Analysis
              ├─► Visualizations
              └─► LaTeX Tables
```

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Dify API access with API key
- Sufficient API credits for 100 campaigns

## Installation

### 1. Clone or Download the Project

```bash
cd eventaic-research
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup PostgreSQL Database

Create a new database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE eventaic_research;
CREATE USER eventaic_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE eventaic_research TO eventaic_user;
\q
```

### 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your configuration:

```env
# Dify API Configuration
DIFY_API_BASE_URL=http://agents.algolyzerlab.com/v1
DIFY_API_KEY=your_actual_api_key_here

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eventaic_research
POSTGRES_USER=eventaic_user
POSTGRES_PASSWORD=your_secure_password_here

# Research Configuration
TOTAL_CAMPAIGNS=100
PRODUCTS_COUNT=10
EVENTS_COUNT=10
```

## Usage

### Initialize Database

First, initialize the database schema:

```bash
python main.py --init-db
```

### Generate Campaigns

Generate all 100 campaigns:

```bash
python main.py --mode generate
```

Generate a specific number of campaigns:

```bash
python main.py --mode generate --campaigns 10
```

### Analyze Data

After campaigns are generated, analyze the results:

```bash
python main.py --mode analyze
```

### Full Pipeline

Run both generation and analysis:

```bash
python main.py --mode all
```

Or simply:

```bash
python main.py
```

## Output Files

### Database Tables

The system creates the following tables in PostgreSQL:

1. **campaigns** - Main campaign metadata
2. **text_content** - Generated text (headlines, descriptions, CTAs)
3. **images** - Generated image metadata and URLs
4. **evaluations** - Quality scores and feedback
5. **timing_metrics** - Generation time for each stage
6. **cost_metrics** - Cost breakdown per campaign

### Analysis Results (`analysis_results/` directory)

1. **campaign_data.csv** - Complete dataset in CSV format
2. **statistics.json** - Summary statistics and test results
3. **Visualizations:**
   - `generation_time_by_config.png` - Timing comparison
   - `quality_scores_distribution.png` - Score distributions
   - `scores_by_product.png` - Quality by product category
   - `cost_vs_quality.png` - Cost-benefit analysis
   - `heatmap_product_event.png` - Performance matrix
4. **LaTeX Tables:**
   - `table_summary_stats.tex` - Summary statistics table
   - `table_model_config.tex` - Performance by configuration

## Research Outputs

### Key Metrics Collected

**Timing Metrics:**
- Text generation time
- Image generation time
- Evaluation time
- Total generation time

**Quality Scores (0-10 scale):**
- Relevance score
- Clarity score
- Persuasiveness score
- Brand safety score
- Overall score

**Cost Metrics:**
- Token usage (prompt/completion)
- Cost per stage
- Total cost per campaign

### Statistical Analysis

The system automatically performs:

1. **Descriptive Statistics**
   - Mean and standard deviation for all metrics
   - Distribution analysis

2. **ANOVA Tests**
   - Compare performance across model configurations
   - Identify significant differences

3. **Correlation Analysis**
   - Relationship between generation time and quality
   - Cost-benefit trade-offs

4. **T-Tests**
   - Compare speed vs quality configurations

## Data Collection Process

For each campaign, the system:

1. **Generates Text Content** (~5-15 seconds)
   - Sends product type and event type to Dify
   - Receives JSON with headline, description, CTA, keywords
   - Stores in database with timing

2. **Generates Image** (~10-30 seconds)
   - Creates prompt from text content
   - Uses FLUX.1 model via Together AI
   - Stores image URL and metadata

3. **Evaluates Campaign** (~5-10 seconds)
   - Sends complete campaign for evaluation
   - Receives scores and recommendations
   - Stores evaluation results

4. **Records Metrics**
   - Timing for each stage
   - API costs and token usage
   - Complete metadata

## Model Configurations

The system tests three configurations:

1. **Speed** - FLUX.1 Schnell (4 steps)
   - Fastest generation
   - Lower cost
   - Good quality

2. **Balanced** - FLUX.1 Dev (20 steps)
   - Balanced performance
   - Moderate cost
   - Better quality

3. **Quality** - FLUX.1 Pro (50+ steps)
   - Highest quality
   - Highest cost
   - Slowest generation

## Product Types × Event Types

**Products:** Smartphone, Laptop, Smartwatch, Headphones, Tablet, Gaming Console, Camera, Fitness Tracker, E-reader, Smart Home Device

**Events:** Black Friday, Christmas, New Year, Valentine's Day, Mother's Day, Back to School, Summer Sale, Cyber Monday, Father's Day, Halloween

This creates 100 unique campaign combinations.

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U eventaic_user -d eventaic_research -h localhost
```

### API Errors

- Check API key is correct in `.env`
- Verify API has sufficient credits
- Check network connectivity to Dify API

### Generation Failures

- Review logs in `eventaic_research.log`
- Check individual campaign status in database:

```sql
SELECT campaign_number, status, product_type, event_type 
FROM campaigns 
WHERE status = 'failed';
```

### Memory Issues

If processing large datasets:

```bash
# Generate in smaller batches
python main.py --mode generate --campaigns 25
```

## Monitoring Progress

The system provides:

1. **Real-time Progress Bar** (via tqdm)
2. **Detailed Logging** to console and file
3. **Database Status** - Query anytime:

```sql
SELECT 
    status, 
    COUNT(*) as count 
FROM campaigns 
GROUP BY status;
```

## Data Quality Checks

Before final analysis, verify:

```sql
-- Check completion rate
SELECT 
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*), 2) as completion_rate
FROM campaigns;

-- Check for missing evaluations
SELECT COUNT(*) 
FROM campaigns c
LEFT JOIN evaluations e ON c.id = e.campaign_id
WHERE c.status = 'completed' AND e.id IS NULL;
```

## Performance Expectations

**For 100 campaigns:**
- **Total Time:** ~30-60 minutes
- **Total Cost:** ~$5-15 USD (varies by API pricing)
- **Database Size:** ~50-100 MB
- **Success Rate:** >95% expected

## Research Paper Integration

Use the generated outputs in your paper:

1. **Section V (Results):**
   - Import `table_summary_stats.tex`
   - Reference `statistics.json` for numbers

2. **Figures:**
   - Include PNG visualizations
   - Use high-resolution (300 DPI) versions

3. **Statistical Tests:**
   - Report p-values from `statistics.json`
   - Include effect sizes

## Extending the System

### Add More Products/Events

Edit `campaign_generator.py`:

```python
PRODUCT_TYPES = [
    # Add your products here
]

EVENT_TYPES = [
    # Add your events here
]
```

### Custom Metrics

Add fields to database models in `database.py` and update the analyzer.

### Different Analysis

Modify `data_analyzer.py` to add custom visualizations or statistical tests.

## License

This research code is provided for academic purposes.

## Citation

If you use this system in your research, please cite:

```bibtex
@article{eventaic2025,
  title={Automated Advertising Campaign Generation from Minimal Prompts: An AI-Powered Multi-Component Approach},
  author={[Shamsuddin Ahmed]},
  journal={[]},
  year={2025}
}
```

## Support

For issues or questions:
1. Check the logs: `eventaic_research.log`
2. Review database status
3. Verify API connectivity
4. Check environment variables

## Acknowledgments

- Dify platform for workflow orchestration
- Together AI for image generation
- Black Forest Labs for FLUX.1 models
