# Wykra API

Wykra is an open-source, build-in-public discovery agent that helps founders, marketers and small teams find the people and communities shaping attention in their niche.

Originally built as a [hackathon prototype](http://dev.to/olgabraginskaya/wykra-web-you-know-real-time-analysis-20i3?ref=datobra.com) ("find people talking about bread in Barcelona"), it's now being rebuilt as a clean, self-hostable FastAPI backend with a simple API for influencer and community discovery powered by Bright Data and LLM analysis.

## Why

Discovery shouldn't mean ten open tabs, half-broken spreadsheets, and guessing which voices actually matter.

Our goals:

- Make discovery transparent, not a black box.

- Balance real-time data with realistic costs.

- Keep it open-source, so anyone can self-host, extend or contribute.

## Current functionality (Week 1 snapshot)

- Provide an Instagram username.

- The API uses [Bright Data's Scraper](https://brightdata.com/products/web-scraper/instagram/profiles) to fetch public profile details.

- It selects key fields (bio, followers, engagement, categories, etc.).

- Builds a natural-language prompt.

- Sends it to an LLM via OpenRouter for contextual analysis.

- Returns a structured insight about the profile.

## Tech stack snapshot

- **Framework**: FastAPI (Python 3.13+)

- **LLM orchestration**: Pydantic AI (Anthropic Claude, OpenAI, others via OpenRouter)

- **HTTP client**: httpx

- **Configuration**: python-dotenv

## Getting started

We are building everything in the open from the first commit. If documentation is missing or unclear, open an issue or ping us. We would rather answer questions than ship guesswork.

### Bright Data setup

Bright Data offers free starter credits so you can test the setup without paying upfront, claim them here: [Bright Data free trial](https://get.brightdata.com/30ufd).

1. Generate a Bright Data API key from the account dashboard. Follow the steps in the Bright Data docs: [How do I generate a new API key?](https://docs.brightdata.com/api-reference/authentication#how-do-i-generate-a-new-api-key%3F).

2. Make sure you have access to the Instagram Web Scraper. The scraper capabilities are documented here: [Instagram API Scrapers](https://docs.brightdata.com/api-reference/web-scraper-api/social-media-apis/instagram).

3. Review the available datasets and pick the one that fits your use case (Instagram is the default). Dataset terminology and the dataset catalog live here: [Dataset ID](https://docs.brightdata.com/api-reference/terminology#dataset-id) and [Get dataset list](https://docs.brightdata.com/api-reference/marketplace-dataset-api/get-dataset-list).

4. Copy the API key into `.env` (see `.env.example` for the exact variable name).

### OpenRouter setup

OpenRouter provides unified access to multiple LLMs (Claude, GPT-4, Gemini, etc.) without hard rate limits.

1. Create an account on OpenRouter and generate an API key in the dashboard: [OpenRouter API keys](https://openrouter.ai/docs/quickstart).

2. Drop the key into `.env` as `OPENROUTER_API_KEY`.

3. (Optional) Pick a model from the [OpenRouter catalog](https://openrouter.ai/models) and set `OPENROUTER_MODEL` if you want something other than the default.

4. Leave `OPENROUTER_BASE_URL` and timeout as-is unless you have a custom proxy or need different latency settings.

### Clone and configure

```bash
git clone https://github.com/wykra-io/wykra-api-python
cd wykra-api-python
cp .env.example .env  # add your keys here
```

<details>
<summary><strong>Run the project</strong></summary>

### Local setup

#### 1. Install Python with pyenv

Make sure you have [pyenv](https://github.com/pyenv/pyenv) installed.

Then install the desired Python version (we'll use 3.13.9):

```bash
pyenv install 3.13.9
```

If pyenv doesn't recognize this Python version, update it first (for macOS + Homebrew users):

```bash
brew update && brew upgrade pyenv
```

If you encounter the following error while building Python:

```
ModuleNotFoundError: No module named '_lzma'
```

just install the missing dependencies:

```bash
brew install readline xz
```

#### 2. Create a Virtual Environment

In the project root, create and activate a dedicated virtual environment:

```bash
pyenv virtualenv 3.13.9 wykra-api-python
pyenv local wykra-api-python
```

This automatically creates a `.python-version` file so your shell uses the correct environment each time you `cd` into the repo.

#### 3. Install Dependencies

Install all project requirements:

```bash
pip install -r requirements.txt
```

#### 4. Environment Variables

Create a local `.env` file (based on the provided `.env.example`):

```bash
cp .env.example .env
```

Then edit `.env` and fill in your own keys and dataset IDs:

```env
BRIGHTDATA_API_TOKEN=your_brightdata_api_token
BRIGHTDATA_INSTAGRAM_DATASET_ID=your_instagram_dataset_id
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

#### 5. Run the API Locally

Spin up the app directly:

```bash
uvicorn app.main:app --reload --port 3011
```

Visit:
- `http://localhost:3011/health`
- `http://localhost:3011/api/v1/instagram/analysis?profile=someusername`

#### 6. Quick Check

```bash
curl http://localhost:3011/health
# -> {"status": "ok", "environment": "local"}
```

If that works — congrats, your local environment is ready 🎉

### Docker

```bash
docker build -t wykra-api-python .
docker run --env-file .env -p 3011:3011 wykra-api-python
```

### Docker Compose

**Full stack (API + any additional services):**

```bash
docker-compose up -d
docker-compose logs -f api
docker-compose down

# remove persistent volumes if needed
docker-compose down -v
```

**Dev services only (run API locally, use Docker for other services):**

```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml down
```

</details>

### Try the API

Once the server is running (locally or via Docker), you can hit the analysis endpoint in two ways:

- **Browser**: open `http://localhost:3011/api/v1/instagram/analysis?profile=<profile_name>` to view the JSON response. A short video walkthrough is coming soon.

- **cURL**:

  ```bash
  curl "http://localhost:3011/api/v1/instagram/analysis?profile=<profile_name>"
  ```

  Replace `<profile_name>` with the Instagram handle you want to inspect.

### Environment variables

Required core config:

- `BRIGHTDATA_API_TOKEN` - Your Bright Data API token
- `BRIGHTDATA_INSTAGRAM_DATASET_ID` - Your Instagram dataset/scraper ID
- `OPENROUTER_API_KEY` - Your OpenRouter API key

Optional integrations:

- `OPENROUTER_MODEL` - Model to use (default: `anthropic/claude-3.5-sonnet`)
- `ENVIRONMENT` - Environment name (default: `local`)

Check `.env.example` for defaults and comments.

## Code Style & Conventions

- All code lives under `app/`
- Configuration lives in `app/core/config.py`
- Agents go in `app/agents/`
- Each route under `app/api/routes/`
- Services in `app/services/`
- Models in `app/models/`
- Follow Pydantic v2 and FastAPI typing conventions

## Contributing

- Open an issue for any bug report, feature idea or question. Context helps — include logs, steps to reproduce or links to relevant discussions.

- Before starting bigger changes, propose them in an issue so we can confirm scope and direction together.

- Keep pull requests focused. Describe your approach, any trade-offs, and how you tested the change.

- Reference the issue number in your PR description and include screenshots or sample responses when it clarifies the outcome.

- We build everything in public, from commits to mistakes. Be kind, be curious, and let's keep the conversation welcoming.

## Project structure

```
wykra-api-python/
├── app/              # Main application code
│   ├── agents/       # AI agents (Pydantic AI)
│   ├── api/          # API routes
│   │   └── routes/   # Individual route modules
│   ├── core/         # Core configuration
│   ├── models/       # Pydantic models
│   ├── services/     # External service integrations
│   └── main.py       # FastAPI application entry point
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Staying in the loop

- Weekly build-in-public posts on Dev.to (https://dev.to/olgabraginskaya/build-in-public-day-zero-end).

- Quick updates and questions on X/Twitter: [@ohthatdatagirl](https://x.com/ohthatdatagirl).

- Star or watch the repo to see weekly progress.

## Thanks

If you are using Wykra, contributing code or sharing feedback, you are part of this build. Let's make "find the right people to talk to" a workflow instead of a stress test.

