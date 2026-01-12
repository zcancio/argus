# Argus
*The hundred-eyed monitor*

Argus is a recreation of the results from ["AI Control: Improving Safety Despite Intentional Subversion"](https://arxiv.org/abs/2312.06942) (Greenblatt et al.).

In the paper, a trusted monitor is used to try and control an untrusted monitor. For the paper and in this recreation, we use GPT-3.5 as the trusted monitor and GPT-4o as the untrusted monitor. Our results appear on par with the paper. We used a smaller problem dataset to reduce cost, but the small sample size still behaves similarly to the large sample used in the paper. Our recreation utilizes the same procedures and prompts. The main difference (other than a smaller sample size) was that we used Python instead of C++ for generating solutions and backdoors.

This project was made possible by leveraging Claude Code extensively. We collaborated with Claude Opus 4.5 on creating the pipeline for pre-computation and simulation.

For detailed learnings and reflections from building this project, see [LEARNINGS.md](./LEARNINGS.md).

---

## CLI Usage

Install the CLI:

```bash
pip install -e .
```

### Dataset Commands

```bash
# Generate a new dataset
argus dataset generate paper_replication -n 75 --chunk 10

# Run more problems in parallel
argus dataset run paper_baseline_75 --add 25 --workers 3

# List datasets
argus dataset list

# Show dataset details
argus dataset info paper_baseline_75
```

### Filter APPS Problems

```bash
# Filter APPS dataset (required before generating datasets)
argus apps filter
```

### Run Simulations

```bash
# Run simulation with Trusted Monitoring
argus simulate paper_baseline_75 --protocol tm --defer-rate 0.10

# Run with Trusted Editing
argus simulate paper_baseline_75 --protocol te --defer-rate 0.20

# Output as JSON
argus simulate paper_baseline_75 --protocol um --json
```

---

## Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/argus)

Or manually:

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

That's it! Frontend + Python API both run on Vercel.

## Local Development

```bash
# Install frontend dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Run dev server
vercel dev
```

## Add Persistent Storage (Optional)

By default, experiments are stored in-memory and reset on cold starts. To persist experiments:

### 1. Create Vercel KV Database

```bash
# In your project directory
vercel link                    # Link to your Vercel project
vercel storage add kv          # Create KV database
```

Or via dashboard:
1. Go to your project on vercel.com
2. Click "Storage" tab
3. Click "Create Database" → "KV"
4. Name it (e.g., "argus-experiments")
5. Click "Connect"

### 2. Redeploy

```bash
vercel --prod
```

The environment variables (`KV_URL`, etc.) are automatically added. The app will detect KV and use it.

**Free tier**: 30,000 requests/month, 256MB storage — plenty for a portfolio project.

## Architecture

```
argus/
├── src/              # React frontend
│   ├── App.jsx
│   ├── components/
│   └── main.jsx
├── api/              # Python serverless functions
│   ├── index.py      # FastAPI app
│   └── _lib/         # Shared modules
│       ├── simulation.py   # Monte Carlo simulation
│       ├── precompute/     # Pre-computation pipeline
│       └── dataset/        # Dataset management
├── datasets/         # Pre-computed problem datasets
├── scripts/          # Dataset generation scripts
└── vercel.json
```

## How It Works

1. **Pre-computation**: Problems are pre-computed with solutions, backdoors, and suspicion scores
2. **Simulation**: Monte Carlo trials sample from the dataset to estimate safety/usefulness
3. **Protocols**: Different monitoring strategies (Trusted Monitoring, Untrusted Monitoring, Trusted Editing)

## Learn More

- [LEARNINGS.md](./LEARNINGS.md) - Detailed learnings from building this project
- [Original Paper](https://arxiv.org/abs/2312.06942) - "AI Control: Improving Safety Despite Intentional Subversion"
