# CTI Sentinel

CTI Sentinel combines a MongoDB lab workspace, a threat-intelligence dashboard and a chat assistant. The assistant can use OpenAI or Ollama. It retrieves educational defensive guidance by platform and threat stage and displays the sources returned from MongoDB.

## One-click Windows demo

Open Docker Desktop and wait for the engine to be ready. Double-click
`start-demo.bat` in the extracted project. It reuses or starts the Docker lab,
checks Ollama and downloads missing models, installs the dependencies, loads
demo data into `ctiSentinelDemo`, and opens the browser. Python, Node.js, Docker
Desktop and Ollama must already be installed. The first run may take time.
Close any earlier CTI Sentinel servers before running it.

The launcher uses local Ollama for this run. It leaves your existing `.env`
untouched. Use the manual setup below to run with OpenAI or an existing database.

## Run on Windows

Use Python 3.10+, Docker Desktop with Linux containers, and a supported Node.js release. Run these from the folder containing `start-windows.bat`.

```powershell
python -m pip install -r requirements.txt
npm.cmd --prefix frontend ci
docker compose -f docker-compose-labs.yml up -d
docker exec cti-mongo-labs mongosh --quiet --eval "rs.initiate({_id:'rs0',members:[{_id:0,host:'localhost:27017'}]})"
```

Run replica-set initialization once for a new volume. An already-initialized message is expected on an existing volume. Use `docker exec cti-mongo-labs mongosh --quiet --eval "db.hello().isWritablePrimary"` and wait for `true`.

Copy `.env.example` to `.env` if needed. Preserve a working app database URI. If you want both the app and lab databases on the Docker test server, use the following settings. The two workloads use different database names on the same isolated server.

```dotenv
MONGO_URI=mongodb://127.0.0.1:27019/?directConnection=true
MONGO_LABS_URI=mongodb://127.0.0.1:27019/?directConnection=true
ENABLE_LAB_RUNNER=1
AI_PROVIDER=openai
OPENAI_API_KEY=replace_this_with_your_own_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
```

Keep the key in your private `.env`. Scoped chat sends the question, recent chat history and the retrieved educational excerpts to OpenAI. Run these commands from the project root:

```powershell
python -m backend.scripts.ingest_threat_knowledge
.\start-windows.bat
```

Open **http://localhost:5173**. In **AI assistant**, send a general question to verify model access. Then choose **Windows → Active** and ask “How should I contain suspected Windows ransomware?” The response should include a source link. To load the optional synthetic threat dashboard records on a test database, run `python -m backend.scripts.seed` separately.

## Docker chat deployment

Use the OpenAI settings above in `.env`. Close the Windows Flask server before starting the Docker chat stack because both use port 5000.

```powershell
docker compose -f docker-compose.app.yml up -d --build mongo cti-sentinel
docker compose -f docker-compose.app.yml exec cti-sentinel python -m backend.scripts.ingest_threat_knowledge
docker compose -f docker-compose.app.yml ps
```

Open **http://localhost:5000**. MongoDB stays on the Docker network in this mode. Use the Windows launcher and separate lab server for write-enabled assignments. For the local Ollama alternative, see [Ollama setup](docs/OLLAMA_SETUP.md).

## Chapters 1–18

Use **MongoDB labs** for the full catalog. Where chat execution is listed, send an exact request such as `run lab 3.1`. A setup check or simulation has its own result criteria.

| Chapter | First experiment | Second experiment | How to demonstrate |
|---|---|---|---|
| 1 | Classify database products | Match data models to workloads | Run 1.1 and 1.2. Show the four NoSQL families and application recommendations. |
| 2 | Compare MongoDB environments | Bookstore CRUD | Run 2.1 and 2.2. Set `MONGO_URI_ATLAS` for the full version comparison. Show the before and after book prices. |
| 3 | Embedded course documents | Migrate referenced comments | Run 3.1 and 3.2. Show Monday courses, rosters and the joined or embedded comments. |
| 4 | Inventory filtering and pagination | Upserts and bulk changes | Run 4.1 and 4.2. Show the filtered products and the second import creating zero duplicates. |
| 5 | Sales aggregation | Lookup joins | Run 5.1 and 5.2. Show revenue by category and the product with no orders. |
| 6 | Design indexes for workloads | Compare index strategies | Run 6.1 and 6.2. Show documents examined before and after indexing and the covered query result. |
| 7 | Schema analysis | Working-set profiling | Use the dedicated **Schema analysis** and **Working-set profiler** screens. Seed the test app database first. |
| 8 | Deploy a replica set | Observe member health and failover | Use the deployment exercise and the 8.2 inspection. Show the single-node replica set for topology. A failover demonstration needs multiple members. |
| 9 | Write-concern benchmark | Network partition exercise | Run 9.1 from **MongoDB labs** with confirmation on a dedicated three-member replica set. 9.2 is a separate infrastructure exercise. |
| 10 | Atomic bank transfer | Concurrent stock reservation | Run 10.1 and 10.2 against the isolated replica set. Show the rollback result and remaining stock. |
| 11 | Shard-key ranking | Simulated distribution | Run 11.1 and 11.2. The first uses illustrative scores. The second writes synthetic data and computes simulated buckets. |
| 12 | Inspect authenticated roles | Verify TLS connectivity | Run the setup checks. Use a configured RBAC test server and a TLS-enabled instance for the respective demonstrations. |
| 13 | Deployment with Compose and Atlas configuration | Kubernetes StatefulSet | Show the running local Compose deployment as supporting evidence. The production deployment and Kubernetes exercise require dedicated infrastructure. |
| 14 | Read server metrics | Backup and restore | Run 14.1 for connections and cache counters. Demonstrate 14.2 against a disposable restore destination with Database Tools. |
| 15 | Tenant-scoped REST API | Tenant migration | Use the standalone exercises in `assignments/chapter_15` with a dedicated dataset; the dashboard lists them as manual. |
| 16 | Compare database schemas | Hybrid query service | Run 16.1 offline. 16.2 needs live MongoDB, Cassandra and Neo4j and is manual. |
| 17 | Retrieval-augmented generation | Compare vector search methods | Show source-backed chat as evidence of local cosine retrieval for 17.1. The standalone Atlas exercise requires Atlas Vector Search. Run 17.2 for the offline simulation. |
| 18 | Measure four MongoDB workloads | Generate the comparison report | Run 18.1 and 18.2. Show the measured MongoDB results and separately labeled Cassandra and Neo4j estimates. |

See [the presentation walkthrough](docs/PRESENTATION_WALKTHROUGH.md) for the demo sequence and evidence checks. The lab catalog entries include setup requirements and source previews. See [verification and standalone commands](docs/RUNNING_AND_TEST_STATUS.md) for recorded results and prerequisites. Run `python -m unittest discover -s tests` to verify the Python tests.

## Scan your Windows computer

The **Computer security scan** navigation item performs five fixed, read-only checks on the Windows computer hosting the Python backend. It checks Microsoft Defender, firewall profiles, system drive encryption, UAC, and recent hotfix history. Findings include evidence and manual remediation guidance. Missing permissions or components appear as **Unavailable**, never as a successful check. This is a security posture review, not a malware scanner or a complete CVE assessment. Defender findings do not assess third-party antivirus products, and hotfix age does not establish patch completeness.

Start Docker Desktop for MongoDB. In the project root PowerShell terminal, enable the scanner before starting the app:

```powershell
$env:ENABLE_HOST_SCAN="1"
.\start-demo.bat
```

Alternatively set `ENABLE_HOST_SCAN=1` in `.env` and restart the backend. Open the app, select **Computer security scan**, read the disclosure, check the consent box, and click **Scan this computer**. Allow up to 75 seconds. Use **Download report** to export JSON for your demonstration. Review Windows settings using the guidance shown. No settings are modified automatically.

Run the backend directly on Windows. The app inside a Linux Docker container cannot inspect the Windows host. The scanner is disabled by default, restricted to loopback requests, rejects untrusted browser origins, and requires explicit consent plus a per-process request token. It runs only fixed PowerShell commands, never commands generated by chat. Results are held in the browser page, not stored in MongoDB or sent to OpenAI/Ollama. No personal files or file contents are collected. A scan does not start a background service.
