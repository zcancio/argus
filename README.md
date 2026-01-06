# ARGUS - AI Control Protocol Benchmark

A framework for evaluating AI control protocols. Deploy to Vercel with one click.

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

## Local Development

```bash
# Install frontend dependencies
npm install

# Run dev server (frontend only, in-memory storage)
npm run dev

# To run with local Python API:
pip install fastapi uvicorn httpx pydantic redis
cd api && uvicorn index:app --reload
```

## Architecture

```
argus/
├── src/              # React frontend
│   ├── App.jsx
│   └── main.jsx
├── api/              # Python serverless functions
│   ├── index.py      # FastAPI app
│   └── _lib/         # Shared modules
│       ├── core.py
│       ├── protocols.py
│       ├── environments.py
│       └── storage.py    # Vercel KV integration
├── package.json
├── requirements.txt
└── vercel.json
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api` | GET | Health check, shows storage status |
| `/api/experiments/run` | POST | Run new experiment |
| `/api/experiments` | GET | List all experiments |
| `/api/experiments/{id}` | GET | Get specific experiment |
| `/api/experiments/{id}` | DELETE | Delete experiment |
| `/api/pareto` | GET | Get Pareto frontier data |
| `/api/validate-key` | POST | Validate LLM API key |

## How It Works

**Frontend**: React + Vite dashboard for configuring and visualizing experiments.

**Backend**: Python FastAPI running as Vercel serverless functions.

**Storage**: Vercel KV (Redis) for persistent experiment results. Falls back to in-memory if KV not configured.

**Flow**:
1. User configures protocol parameters
2. Clicks "Run Experiment"
3. API runs N episodes, saves to KV
4. Results displayed + persisted for later

## Limitations

- **10s timeout** (60s on Pro) — keep `num_episodes` under ~200
- **Cold starts** — first request may be slower
- **KV free tier** — 30k requests/month

## Using Real LLM APIs

1. Enter your Anthropic or OpenAI API key
2. Click "Test" to validate
3. Select the provider in dropdowns
4. Run experiment with real models

Keys are sent via headers and never stored.

## Learn More

This implements the Trusted Monitoring protocol from [Greenblatt et al., "AI Control: Improving Safety Despite Intentional Subversion"](https://arxiv.org/abs/2312.06942).

