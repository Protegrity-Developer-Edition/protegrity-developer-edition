# Getting Started

**Date**: 13 May 2026
**Type**: implementation analysis

A step-by-step guide to deploy and use the Protegrity AI Developer Edition
Trial Center on your local machine.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1 — Get Your Credentials](#step-1--get-your-credentials)
- [Step 2 — Clone the Repository](#step-2--clone-the-repository)
- [Step 3 — Configure Credentials](#step-3--configure-credentials)
- [Step 4 — Deploy](#step-4--deploy)
- [Step 5 — Open the Trial Center](#step-5--open-the-trial-center)
- [Using the Trial Center](#using-the-trial-center)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

The Trial Center is **only the UI**. It expects the Protegrity AI Developer
Edition backend services to be installed and running on your machine first.

| Requirement | Minimum Version | How to Install |
|-------------|-----------------|----------------|
| Docker | 20.10+ | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| Docker Compose | 2.0+ | Included with Docker Desktop |
| Protegrity AI Developer Edition account | — | [protegrity.com/developer-edition](https://www.protegrity.com/developer-edition) |
| **Semantic Guardrail** service running on `localhost:8581` | 1.1.1+ | Provided by Protegrity AI Developer Edition install |
| **Classification / Data Discovery** service running on `localhost:8580` | 2.0.0+ | Provided by Protegrity AI Developer Edition install |

> **Important**: The Semantic Guardrail and Classification services are **not**
> started by this repository's `docker compose`. Install and start them via
> the official Protegrity AI Developer Edition deployment first, then start the
> Trial Center UI.

> **Note**: You do **not** need Python installed. The Trial Center UI runs
> entirely inside its own Docker container.

#### Verify Backends Are Running

```bash
curl -sf http://localhost:8581/ -o /dev/null && echo "Guardrail: OK" || echo "Guardrail: NOT REACHABLE"
curl -sf http://localhost:8580/ -o /dev/null && echo "Discovery: OK" || echo "Discovery: NOT REACHABLE"
```

Any HTTP response (including 404 on `/`) means the service is up. The deploy
script (`./scripts/deploy.sh --check`) performs this check automatically.

#### Verify Docker is Ready

```bash
docker --version        # Should show >= 20.10
docker compose version  # Should show >= 2.0
```

#### Platform Note (Apple Silicon / arm64)

The Protegrity AI Developer Edition backend images are currently published for
`linux/amd64` only. On Apple Silicon and other arm64 hosts they run via
Rosetta / QEMU emulation. This is fine for trial / exploration use but
slower than native; multi-arch images are tracked upstream by Protegrity.

---

## Step 1 — Get Your Credentials

1. Go to [protegrity.com/developer-edition](https://www.protegrity.com/developer-edition)
2. Sign up or log in to your Protegrity AI Developer Edition account
3. Note down three values:
   - **Email** — the email you registered with
   - **Password** — your account password
   - **API Key** — found in your Developer Edition dashboard

---

## Step 2 — Clone the Repository

The Trial Center ships as the `trial-center/` subfolder of the Protegrity AI
Developer Edition repository.

```bash
git clone https://github.com/Protegrity-AI-Developer-Edition/protegrity-ai-developer-edition.git
cd protegrity-ai-developer-edition
git checkout pre-release-1.2.0
cd trial-center
```

---

## Step 3 — Configure Credentials

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your credentials:

```dotenv
DEV_EDITION_EMAIL=your-email@example.com
DEV_EDITION_PASSWORD=your-password-here
DEV_EDITION_API_KEY=your-api-key-here
```

> **Security**: The `.env` file is git-ignored and never committed.

---

## Step 4 — Deploy

#### Option A: Using the Deploy Script (Recommended)

```bash
./scripts/deploy.sh
```

The script will:

1. Check all prerequisites (Docker, Compose, ports, credentials)
2. Show a comparison table of what is ready vs what is missing
3. Ask for confirmation before proceeding
4. Build and start all containers
5. Wait for services to become healthy
6. Print the access URL

#### Option B: Direct Docker Compose

```bash
docker compose up -d --build
```

#### Windows Users

```cmd
scripts\deploy.bat
```

---

## Step 5 — Open the Trial Center

Once deployment completes, open your browser:

```text
http://localhost:8502
```

You should see the Protegrity AI Developer Edition Trial Center interface.

---

## Using the Trial Center

#### Choose an Execution Mode

The Trial Center offers five modes accessible from the sidebar:

| Mode | What It Does |
|------|--------------|
| **Full Pipeline** | Guardrail → Discover → Protect → Unprotect → Redact |
| **Semantic Guardrail** | Scores prompt risk without modifying content |
| **Discover Sensitive Data** | Identifies PII/PHI/PCI entities in the prompt |
| **Find, Protect & Unprotect** | Discovers entities, protects them, then reverses |
| **Find & Redact** | Discovers entities and permanently removes them |

#### Enter a Prompt

1. Select a **domain** from the dropdown (e.g., `customer-support`, `financial`, `health`)
2. Type or paste a prompt containing sensitive data
3. Click **Run**

#### Read the Results

The output shows:

- **Guardrail Score** — risk assessment with pass/fail outcome
- **Discovered Entities** — table of detected PII with types and positions
- **Protected Output** — the sanitised prompt with entities masked or redacted
- **Unprotected Output** — round-trip verification (protect mode only)

#### Example Prompts to Try

```text
My name is John Smith, my SSN is 123-45-6789, and my email is john@example.com.
Please transfer $5000 from account 4111-1111-1111-1111 to savings.
Patient Jane Doe, DOB 03/15/1985, diagnosed with hypertension.
```

---

## Common Operations

#### Check Service Status

```bash
docker compose ps
```

#### View Logs

```bash
./scripts/deploy.sh --logs
# or directly:
docker compose logs -f
```

#### Stop All Services

```bash
./scripts/deploy.sh --clean
# or directly:
docker compose down
```

#### Restart After a Code Change

```bash
docker compose up -d --build
```

#### Run on a Different Port

```bash
TRIAL_CENTER_PORT=9000 ./scripts/deploy.sh
```

---

## Troubleshooting

#### "Port 8502 is already in use"

Another process is using the port. Either stop it or use a different port:

```bash
# Find what's using the port
lsof -i :8502

# Use a different port
TRIAL_CENTER_PORT=8503 ./scripts/deploy.sh
```

#### "Credentials not configured" warning

The UI launches but protection operations will fail. Ensure your `.env` file
exists and contains valid values:

```bash
cat .env  # Verify it has all three variables filled
```

#### Container exits immediately

Check the container logs:

```bash
docker compose logs trial-center
```

If the issue is a backend-service problem, inspect the logs of the Protegrity
Developer Edition backend you started separately (Semantic Guardrail,
Classification Service).

#### "Docker daemon not running"

Start Docker Desktop (macOS/Windows) or the Docker service (Linux):

```bash
# Linux
sudo systemctl start docker

# macOS/Windows
# Open Docker Desktop application
```

#### Trial Center loads but "Service Unavailable" for guardrail/discovery

The Trial Center cannot reach the Protegrity backend services. Check:

1. The backends are actually running on the host:

   ```bash
   curl -sf http://localhost:8581/ -o /dev/null && echo OK || echo DOWN
   curl -sf http://localhost:8580/ -o /dev/null && echo OK || echo DOWN
   ```

2. The Trial Center container can reach them. From inside the container:

   ```bash
   docker exec trial-center python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:8581/', timeout=3).status)"
   ```

3. If your backends run on a different host or port, set
   `SEMANTIC_GUARDRAIL_URL` / `CLASSIFICATION_SERVICE_URL` in `.env` and
   restart with `docker compose up -d`.

#### Prerequisite check fails

Run the check independently to see all issues at once:

```bash
./scripts/deploy.sh --check
```

---

## Next Steps

- Read the [Architecture](ARCHITECTURE.md) document for technical details
- Visit the [Developer Documentation](https://developer.docs.protegrity.com/docs/)
  for API reference and advanced usage
- Explore sample prompts in the `samples/` directory
