# Verification on 24 November 2026

Code tested at commit `26cea965f4e155d252d422aa6e384b9ef5230a1e` in a Linux workspace. These results do not certify every exercise on a student's Windows computer.

## Completed in this run

- All 20 Python automated tests passed, including opt-in host-scan authorization and mocked Windows check evaluation.
- React/Vite production build passed. Python compilation and Bash syntax checks passed.
- All 36 exercises were present in the catalog. 26 applicable HTTP lab operations returned successfully against a newly created disposable MongoDB 7 replica set. Of these, 19 explicitly reported `passed: true`; the others return metrics, setup information, or readiness rather than a pass verdict. HTTP success alone is not a completed exercise.
- Chapter 7.1 schema, BSON size, and benchmark operations succeeded. Chapter 7.2 loaded 100,000 documents, completed its loader without errors, read metrics, and ran 500 random reads.
- The standalone Chapter 15 tenant examples, Chapter 16 graph fallback, and Chapter 17 sample RAG pipeline exited successfully. Chapter 17.1 uses mock embeddings and sample answers. Chapter 17.2 is the reduced offline vector simulation.
- Separate secured MongoDB checks verified Chapter 12 role restrictions and TLS. Analyst writes and cross-database access were denied, writer updates succeeded, plaintext connections were rejected, and the TLS dashboard check passed with a trusted test CA.
- Chapter 9.1 completed all 6,000 writes across six write-concern/journaling settings on two data nodes and one arbiter with keyfile authentication. The disposable test servers used a 1 ms journal commit interval to keep functional verification short. These timings are not a performance prediction. The initial run at the default interval was interrupted before completion. Anonymous replica status access was rejected and authenticated status succeeded.
- Chapter 13.2 generated all four Kubernetes manifests. No live Kubernetes deployment was performed.

## Still requires additional verification

- Chapter 2.1 Atlas comparison needs an Atlas URI.
- Chapter 8.1 full three-container Docker launch and Chapter 8.2 failover need the dedicated replica-set topology. The one-node status endpoint alone does not test failover. Prior native-process failover evidence is described in RUNNING_AND_TEST_STATUS.md.
- Chapter 9.2 live Docker network partition and recovery have not been verified.
- Chapter 13.1 native keyfile authentication was checked; the full separate-container deployment has not been verified.
- Chapter 13.2 Kubernetes rollout and initialization Job require a live disposable cluster.
- Chapter 14.2 checksum restore was verified in the earlier audit; it was not repeated here because MongoDB Database Tools are unavailable.
- Chapter 16.2 live Neo4j integration remains unverified. The course graph fallback ran successfully.
- Windows security posture commands require the native Windows backend. This environment only tests their evaluation and access controls with mocks.
- Live OpenAI calls require a valid API key and billing; provider tests use mocked responses.

See RUNNING_AND_TEST_STATUS.md for the chapter-by-chapter audit and setup commands. Do not present readiness checks, simulated comparisons, or mocked responses as completed live infrastructure exercises.
