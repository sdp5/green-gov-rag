# LLM Configuration Guide

This guide covers configuration and optimization of Large Language Models (LLMs) in GreenGovRAG, including provider setup, model selection, cost optimization, and prompt engineering.

## Table of Contents

- [Supported LLM Providers](#supported-llm-providers)
- [OpenAI Configuration](#openai-configuration)
- [Azure OpenAI Configuration](#azure-openai-configuration)
- [AWS Bedrock Configuration](#aws-bedrock-configuration)
- [Anthropic Configuration](#anthropic-configuration)
- [Model Selection Guide](#model-selection-guide)
- [Cost Optimization](#cost-optimization)
- [Prompt Customization](#prompt-customization)
- [Temperature and Parameter Tuning](#temperature-and-parameter-tuning)

---

## Supported LLM Providers

GreenGovRAG uses a factory pattern to support multiple LLM providers through a unified interface via LangChain.

**Module**: `/backend/green_gov_rag/rag/llm_factory.py`

**Supported Providers**:

| Provider | Models | Strengths | Use Case |
|----------|--------|-----------|----------|
| OpenAI | GPT-4, GPT-4-turbo, GPT-3.5-turbo, GPT-4o | Best general performance | Development, testing |
| Azure OpenAI | Same as OpenAI | Enterprise SLAs, data residency | Production (recommended) |
| AWS Bedrock | Claude 3, Titan, Llama 2 | AWS-native, no API keys | AWS deployments |
| Anthropic | Claude 3 Opus, Sonnet, Haiku | Strong reasoning, long context | Complex regulatory queries |

---

## OpenAI Configuration

### 1. Prerequisites

- OpenAI API key from https://platform.openai.com/api-keys
- Sufficient quota/credits

### 2. Environment Variables

**File**: `/backend/.env`

```bash
# LLM Provider Selection
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini  # or gpt-4, gpt-4-turbo, gpt-3.5-turbo

# Generation Parameters
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=500
```

### 3. Code Example

```python
from green_gov_rag.rag.llm_factory import LLMFactory

# Create LLM instance
llm = LLMFactory.create_llm(
    provider="openai",
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=500
)

# Use in RAG chain
from green_gov_rag.rag.rag_chain import RAGChain

rag_chain = RAGChain(
    vector_store=vector_store,
    llm_provider="openai",
    llm_model="gpt-4o-mini"
)

result = rag_chain.query("What are NGER thresholds?")
```

### 4. Model Comparison

| Model | Speed | Cost | Quality | Max Tokens |
|-------|-------|------|---------|------------|
| gpt-4o-mini | Fast (500ms) | $0.15/1M tokens | Good | 128K |
| gpt-4o | Medium (1s) | $2.50/1M tokens | Excellent | 128K |
| gpt-4-turbo | Medium (1.5s) | $10/1M tokens | Excellent | 128K |
| gpt-3.5-turbo | Very fast (300ms) | $0.50/1M tokens | Good | 16K |

**Recommended**: `gpt-4o-mini` for best cost/performance ratio.

---

## Azure OpenAI Configuration

### 1. Prerequisites

- Azure subscription
- Azure OpenAI resource created in Azure Portal
- Deployment created for specific model (e.g., `gpt-4o-mini`)

### 2. Setup Steps

**Step 1**: Create Azure OpenAI resource
```bash
# Via Azure Portal
1. Navigate to Azure Portal
2. Create Resource → Azure OpenAI
3. Select region (e.g., Australia East)
4. Choose pricing tier (Standard S0)
```

**Step 2**: Create model deployment
```bash
# In Azure OpenAI Studio
1. Go to Deployments
2. Create New Deployment
3. Model: gpt-4o-mini (or gpt-4, gpt-35-turbo)
4. Deployment name: gpt-4o-mini-deployment
5. Deploy
```

**Step 3**: Get credentials
```bash
# From Azure Portal → Your OpenAI Resource → Keys and Endpoint
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Environment Variables

```bash
# LLM Provider Selection
LLM_PROVIDER=azure

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini-deployment  # Your deployment name
AZURE_OPENAI_API_VERSION=2024-02-15-preview     # API version

# Model Selection
LLM_MODEL=gpt-4o-mini  # Base model name

# Generation Parameters
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=500
```

### 4. Code Example

```python
from green_gov_rag.rag.llm_factory import LLMFactory

llm = LLMFactory.create_llm(
    provider="azure",
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=500
)

# Environment variables automatically loaded
# Uses AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
```

### 5. Benefits of Azure OpenAI

****Enterprise SLAs**: 99.9% uptime guarantee
****Data Residency**: Data stays in Australia (Australia East region)
****No API Keys in Code**: Managed Identity support
****Cost Control**: Dedicated capacity prevents rate limiting
****Compliance**: SOC 2, ISO 27001, HIPAA certified

**Pricing** (Australia East):
- gpt-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens
- gpt-4o: $2.50/1M input tokens, $10/1M output tokens

---

## AWS Bedrock Configuration

### 1. Prerequisites

- AWS account with Bedrock access
- IAM user with Bedrock permissions
- Model access enabled in AWS Console

### 2. Enable Model Access

```bash
# Via AWS Console
1. Navigate to AWS Bedrock
2. Model Access → Manage Model Access
3. Enable: Anthropic Claude 3 Sonnet, Claude 3 Haiku, Amazon Titan
4. Request access (usually instant approval)
```

### 3. IAM Permissions

**Policy** (`bedrock-policy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
      ]
    }
  ]
}
```

### 4. Environment Variables

```bash
# LLM Provider Selection
LLM_PROVIDER=bedrock

# AWS Credentials
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1  # Bedrock available in us-east-1, us-west-2, eu-west-1

# Model Selection (Bedrock model ID)
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
# Or: anthropic.claude-3-haiku-20240307-v1:0
# Or: amazon.titan-text-premier-v1:0

# Generation Parameters
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=500
```

### 5. Supported Models

| Model ID | Model | Speed | Cost | Context |
|----------|-------|-------|------|---------|
| anthropic.claude-3-sonnet-20240229-v1:0 | Claude 3 Sonnet | Medium | $3/1M input, $15/1M output | 200K |
| anthropic.claude-3-haiku-20240307-v1:0 | Claude 3 Haiku | Fast | $0.25/1M input, $1.25/1M output | 200K |
| amazon.titan-text-premier-v1:0 | Titan Text Premier | Fast | $0.50/1M tokens | 32K |

### 6. Code Example

```python
llm = LLMFactory.create_llm(
    provider="bedrock",
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    temperature=0.2,
    max_tokens=500
)
```

---

## Anthropic Configuration

### 1. Prerequisites

- Anthropic API key from https://console.anthropic.com/
- Sufficient credits

### 2. Environment Variables

```bash
# LLM Provider Selection
LLM_PROVIDER=anthropic

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx

# Model Selection
LLM_MODEL=claude-3-sonnet-20240229
# Or: claude-3-opus-20240229, claude-3-haiku-20240307

# Generation Parameters
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=500
```

### 3. Model Comparison

| Model | Speed | Cost | Quality | Context |
|-------|-------|------|---------|---------|
| Claude 3 Opus | Slow (3s) | $15/1M input, $75/1M output | Highest | 200K |
| Claude 3 Sonnet | Medium (1.5s) | $3/1M input, $15/1M output | High | 200K |
| Claude 3 Haiku | Fast (500ms) | $0.25/1M input, $1.25/1M output | Good | 200K |

### 4. Code Example

```python
llm = LLMFactory.create_llm(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    temperature=0.2,
    max_tokens=500
)
```

---

## Model Selection Guide

### 1. By Use Case

| Use Case | Recommended Model | Reason |
|----------|-------------------|--------|
| **Production RAG (general)** | Azure gpt-4o-mini | Best cost/performance, enterprise SLA |
| **High-accuracy regulatory** | Claude 3 Sonnet | Strong reasoning, long context |
| **Development/testing** | OpenAI gpt-4o-mini | Fast iteration, low cost |
| **AWS-native deployment** | Bedrock Claude 3 Haiku | No API keys, AWS integrated |
| **Complex legal analysis** | Claude 3 Opus or GPT-4 | Highest quality |
| **Budget-constrained** | gpt-3.5-turbo or Titan | Lowest cost |

### 2. By Latency Requirements

| Latency Requirement | Model | Average Response Time |
|---------------------|-------|----------------------|
| Real-time (<500ms) | gpt-4o-mini, gpt-3.5-turbo | 300-500ms |
| Interactive (<1s) | Claude 3 Haiku, Titan | 500-800ms |
| Standard (<2s) | gpt-4o, Claude 3 Sonnet | 1-1.5s |
| Batch/offline (>2s) | gpt-4-turbo, Claude 3 Opus | 2-3s |

### 3. By Cost Budget

**Monthly Cost Estimates** (100K queries/month, avg 500 input tokens, 200 output tokens):

| Model | Input Cost | Output Cost | Total/Month |
|-------|------------|-------------|-------------|
| gpt-4o-mini | $7.50 | $12 | $19.50 |
| gpt-3.5-turbo | $25 | $50 | $75 |
| Claude 3 Haiku | $12.50 | $25 | $37.50 |
| gpt-4o | $125 | $200 | $325 |
| Claude 3 Sonnet | $150 | $300 | $450 |
| gpt-4-turbo | $500 | $1,000 | $1,500 |

**Recommendation**: Start with `gpt-4o-mini` for production (best value).

---

## Cost Optimization

### 1. Reduce Input Tokens

**Strategy**: Limit number of retrieved documents

```python
# Default: retrieve 5 documents
rag_chain.query(query, k=5)  # ~2000 input tokens

# Optimized: retrieve 3 documents
rag_chain.query(query, k=3)  # ~1200 input tokens (40% reduction)
```

**Trade-off**: May miss relevant context, but reduces cost by 40%.

### 2. Use Smaller Models

```python
# Production (high quality)
LLM_MODEL=gpt-4o-mini  # $0.15/1M input

# Cost-optimized (good quality)
LLM_MODEL=gpt-3.5-turbo  # $0.50/1M input (but faster)
```

### 3. Cache Responses

**Implementation**:
```python
# Enable query caching (default: 1 hour TTL)
# Saves ~30-40% of LLM calls

# In .env
CACHE_ENABLED=true
CACHE_TTL=3600  # 1 hour
```

**Savings**: ~$100/month for typical production workload.

### 4. Adjust Max Tokens

```python
# Default: 500 tokens output (sufficient for most queries)
LLM_MAX_TOKENS=500

# Short answers: 200 tokens
LLM_MAX_TOKENS=200  # 60% cost reduction on output

# Long explanations: 1000 tokens
LLM_MAX_TOKENS=1000  # Increased cost but more detail
```

### 5. Batch Processing

**For ETL metadata tagging**:
```python
# Process 10 documents per batch (reduce API calls)
tagger.tag_all(documents, batch_size=10)

# Add delay between batches to avoid rate limiting
time.sleep(1)  # 1 second delay
```

---

## Prompt Customization

### 1. Default RAG Prompt

**Location**: `/backend/green_gov_rag/rag/rag_chain.py`

**Current Prompt**:
```python
prompt = f"""Answer the query based on the following context:

{context}

Query: {query}

Answer:"""
```

### 2. Enhanced Regulatory Prompt

**Customization**:
```python
prompt = f"""You are an expert assistant for Australian environmental and planning regulations.

Answer the query based ONLY on the provided context. Follow these guidelines:

1. Cite specific sections, clauses, or regulations when available
2. Use exact wording from regulations for definitions and requirements
3. Highlight jurisdiction-specific rules (federal vs. state vs. local)
4. If the context doesn't contain enough information, say so explicitly
5. Use Australian English spelling and terminology
6. Include relevant thresholds, dates, and numeric values

Context:
{context}

Query: {query}

Answer:"""
```

### 3. Domain-Specific Prompts

**For ESG/NGER Queries**:
```python
if "nger" in query.lower() or "emissions" in query.lower():
    prompt = f"""You are an expert in Australian greenhouse gas emissions reporting under NGER.

Answer the query using the provided regulatory context. Always:
- Specify emission scopes (Scope 1, 2, 3)
- Include thresholds in tonnes CO2-e
- Cite relevant NGER legislation sections
- Mention reporting deadlines when applicable

Context:
{context}

Query: {query}

Answer:"""
```

**For Planning/Vegetation Queries**:
```python
if "tree" in query.lower() or "vegetation" in query.lower():
    prompt = f"""You are an expert in Australian planning and vegetation management regulations.

Answer using the provided context. Always:
- Specify LGA-level requirements
- Cite relevant planning schemes
- Mention permit/approval requirements
- Include clearance thresholds (hectares, tree count)

Context:
{context}

Query: {query}

Answer:"""
```

### 4. Few-Shot Examples (Future)

```python
prompt = f"""You are a regulatory expert. Answer based on provided context.

Example 1:
Query: What are NGER thresholds?
Answer: Under NGER, facilities must report Scope 1 emissions exceeding 25,000 tonnes CO2-e annually [Section 2.1.3]. Corporate groups report if total emissions exceed 50,000 tonnes CO2-e [Section 4.2].

Example 2:
Query: Can I clear native vegetation in Adelaide?
Answer: In the City of Adelaide (LGA 40070), native vegetation clearance requires approval under the SA Planning and Design Code [Section 5.3.2]. Exemptions apply for trees <5m height or non-significant vegetation [Clause 42(a)].

Now answer this query:
Context:
{context}

Query: {query}

Answer:"""
```

---

## Temperature and Parameter Tuning

### 1. Temperature Guidelines

**Temperature** controls randomness in LLM responses:

| Temperature | Behavior | Use Case |
|-------------|----------|----------|
| 0.0 | Deterministic, always same output | Regulatory compliance (recommended) |
| 0.1-0.2 | Highly consistent, minimal variation | Default RAG queries |
| 0.3-0.5 | Balanced creativity and consistency | Explanations, summaries |
| 0.6-0.8 | Creative, diverse responses | Ideation, brainstorming |
| 0.9-1.0 | Highly random | Not recommended for regulatory |

**Recommended for GreenGovRAG**: `0.2`

### 2. Max Tokens

**Max Tokens** limits response length:

| Token Limit | Words (~) | Use Case |
|-------------|-----------|----------|
| 100 | 75 | Short answers, definitions |
| 200 | 150 | Concise answers (cost-optimized) |
| 500 | 375 | Default (balanced) |
| 1000 | 750 | Detailed explanations |
| 2000 | 1500 | Comprehensive analysis |

**Recommended**: `500` (sufficient for most regulatory queries)

### 3. Top-P (Nucleus Sampling)

**Top-P** (not currently exposed, but available via LangChain):

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=500,
    top_p=0.9  # Consider top 90% of probability mass
)
```

**Recommendation**: Use default (`top_p=1.0`) for regulatory queries.

### 4. Frequency Penalty

**Frequency Penalty** reduces repetition:

```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=500,
    frequency_penalty=0.5  # Penalize repeated tokens
)
```

**Use Case**: Long-form answers where repetition is undesirable.

### 5. Configuration Examples

**Production RAG (default)**:
```python
llm = LLMFactory.create_llm(
    provider="azure",
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=500
)
```

**High-Precision Regulatory**:
```python
llm = LLMFactory.create_llm(
    provider="azure",
    model="gpt-4o",
    temperature=0.0,  # Deterministic
    max_tokens=300    # Concise
)
```

**Detailed Explanations**:
```python
llm = LLMFactory.create_llm(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    temperature=0.3,  # Slightly more creative
    max_tokens=1000   # Longer responses
)
```

---

## Testing and Validation

### 1. Model A/B Testing

```python
models = [
    {"provider": "azure", "model": "gpt-4o-mini"},
    {"provider": "azure", "model": "gpt-4o"},
    {"provider": "anthropic", "model": "claude-3-sonnet-20240229"}
]

test_queries = [
    "What are NGER Scope 1 thresholds?",
    "Can I clear native vegetation in Adelaide?",
    "What are Scope 3 Category 4 emissions?"
]

for model_config in models:
    llm = LLMFactory.create_llm(**model_config)
    rag_chain = RAGChain(vector_store=vector_store, llm_provider=model_config["provider"])

    for query in test_queries:
        result = rag_chain.query(query)
        print(f"Model: {model_config['model']}")
        print(f"Answer: {result['result']}")
        print(f"Sources: {len(result['source_documents'])}")
        print("---")
```

### 2. Cost Tracking

```python
# Track token usage
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = rag_chain.query(query)

    print(f"Input tokens: {cb.prompt_tokens}")
    print(f"Output tokens: {cb.completion_tokens}")
    print(f"Total cost: ${cb.total_cost:.4f}")
```

---

## Troubleshooting

### 1. Rate Limiting

**Error**: `RateLimitError: Rate limit exceeded`

**Solution**:
```python
# Add exponential backoff
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def query_with_retry(query: str):
    return rag_chain.query(query)
```

### 2. Context Length Exceeded

**Error**: `InvalidRequestError: maximum context length exceeded`

**Solution**:
```python
# Reduce number of retrieved documents
rag_chain.query(query, k=3)  # Instead of k=5

# Or use a model with longer context
LLM_MODEL=gpt-4o  # 128K context vs 16K for gpt-3.5-turbo
```

### 3. Empty Responses

**Issue**: LLM returns empty or very short responses

**Solution**:
```python
# Increase max_tokens
LLM_MAX_TOKENS=1000  # Instead of 500

# Adjust temperature
LLM_TEMPERATURE=0.3  # Instead of 0.2 (less deterministic)
```

---

## Next Steps

1. **Try Different Models**: A/B test multiple models on your queries
2. **Customize Prompts**: Tailor prompts for your specific regulatory domain
3. **Monitor Costs**: Track token usage and optimize accordingly
4. **Read Architecture**: See [architecture/rag-pipeline.md](./architecture/rag-pipeline.md)

---

**Last Updated**: 2025-11-15
**Maintainer**: Sundeep Anand (contact@sundeep.id.au)
