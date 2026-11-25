# Lab verification and standalone exercises

The November 2026 verification used disposable MongoDB 7 data. The dashboard checks exercised the Flask routes. The standalone checks ran the repository scripts. “Needs verification” means the required infrastructure or credentials were unavailable for a complete run.

| Chapter | Exercise 1 | Exercise 2 |
|---|---|---|
| 1 | Product classification passed | Workload-to-database mapping passed |
| 2 | Local server version verified; Atlas comparison needs an Atlas URI | Pre-2010 price update and CRUD passed |
| 3 | Embedded course schema and queries passed | Referenced-to-embedded migration passed |
| 4 | Inventory filters and pagination passed | Bulk update and repeat import passed |
| 5 | Sales analytics passed | Customer and order lookup passed |
| 6 | Query execution statistics and indexing passed | Covered and fetched query comparisons passed |
| 7 | Schema, BSON size and benchmark endpoints succeeded | Loaded 100,000 documents, read cache metrics and ran 500 random reads |
| 8 | Initialized MongoDB and added members in the isolated test container; the three-container Compose launch needs a rerun | Observed the primary change from port 27017 to port 27018 |
| 9 | 6,000 writes across six settings completed with average, P50 and P99 timings | Partition workflow prepared; live network isolation and recovery need verification |
| 10 | Transfer and rollback passed | Concurrent inventory reservation passed |
| 11 | Illustrative shard-key ranking passed | 10,000 synthetic documents bucketed in the distribution simulation |
| 12 | Verified analyst, writer and custom log-writer permissions on a secured test instance | Plaintext was rejected and the dashboard TLS ping succeeded with a trusted test CA |
| 13 | Verified keyfile authentication on three local MongoDB processes; the separate-container Compose deployment still needs a run | All four manifests generated; rollout and Job need a Kubernetes cluster |
| 14 | Read live MongoDB server and cache counters | Restored all 500 documents and matched the content checksum |
| 15 | Tenant-scoped update, cross-tenant rejection and rate limit observed | Dry-run support, verified two copied tasks, and repeated migration retained the count |
| 16 | Offline MongoDB, Cassandra and Neo4j schema comparison passed | MongoDB queries and in-memory graph traversal ran; live Neo4j was unavailable |
| 17 | Four sample turns executed chunk retrieval and prompt construction with mock embeddings, as described in the course README | The dashboard’s reduced offline vector comparison passed |
| 18 | Four live MongoDB workloads measured | Comparative report generated with Cassandra and Neo4j estimates labeled |

## Chapters 8–9 local Docker lab

Use Git Bash from the project root, with Docker Desktop running. This uses
the dedicated `cti-replica-lab` Compose project on host ports 27101–27103. The
one-click database on port 27019 is a separate single-node set.

```bash
bash assignments/chapter_08/lab_8.1_deploy_replicaset.sh
python assignments/chapter_08/lab_8.2_failover_observer.py
```

For the failover experiment, keep the observer running and trigger the step-down
from another terminal using its printed command. For the write-concern benchmark,
configure `MONGO_LABS_URI` to the current writable member’s loopback port with
`directConnection=true`, use the manual Windows launcher, then choose 9.1 in the
dashboard. Its default six settings each run 1,000 writes. For 9.2, with the
Chapter 8 cluster running, use the following command to observe the secondary
before isolation, during isolation, and after it rejoins:

```bash
bash assignments/chapter_09/lab_9.2_simulate_partition.sh
```

## Remaining standalone exercises

For the MongoDB-backed scripts below, set `MONGO_LABS_URI` in your local `.env`
to the disposable lab database. The one-click launcher sets this for its own
process. Set it in your PowerShell session or `.env` when opening a separate terminal.

```powershell
python -m assignments.chapter_14.lab_02_backup_restore
python -m assignments.chapter_15.lab_01_multitenant_api
python -m assignments.chapter_15.lab_02_tenant_migration
python -m assignments.chapter_15.lab_02_tenant_migration --dry-run
python -m assignments.chapter_16.lab_02_hybrid_query_service
python -m assignments.chapter_17.lab_01_rag_pipeline
```

- **12.1 and 12.2** use the secured test instances described in [Chapter 12 setup](CHAPTER_12_SETUP.md).
- **13.1** runs from Git Bash with Docker Desktop and OpenSSL using `bash assignments/chapter_13/lab_01_deploy_prod.sh`. It prompts for a lab-only administrator password and generates a lab keyfile on the first run.
- **13.2** generates the manifests with `python -m assignments.chapter_13.lab_02_k8s_statefulset`. Use `--apply` only when the current Kubernetes context is a disposable lab cluster.
- **14.2** needs `mongodump` and `mongorestore` on PATH. The script backs up and drops only the uniquely named fixture collection it creates, then restores that collection and checks the checksum.
- **16.2** uses the graph fallback unless `NEO4J_URI` and the Neo4j driver are configured. The fallback is part of the course exercise.
- **17.1** uses the course’s mock retrieval exercise. For a live model demonstration, use the assessment chat with its separate embedded threat catalog.
