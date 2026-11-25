# CTI Sentinel presentation walkthrough

## Before the presentation

For the one-click demo, open Docker Desktop and run `start-demo.bat`. In the
examples below, use `ctiSentinelDemo` for chat data and `ollama` for the provider.
You can skip the manual ingestion step in this mode.


1. Follow the Windows setup in the [README](../README.md). Keep Docker Desktop running and keep your API key out of the screen share. Confirm `db.hello().isWritablePrimary` returns `true`.
2. Run the catalog ingestion command. Start the app and test one general message plus one Windows Active threat question. The first confirms OpenAI credentials and model access. The second checks the embeddings, MongoDB retrieval, and cited answer.
3. Open the lab catalog and work through the README table. Record the result immediately. Chapters 8, 9, 12–17 contain exercises that require infrastructure beyond the single-node demo, and some dashboard entries are inspections or simulations. Only report completion when the exercise's required action and evidence are available.

## Show the working system

**1. Docker Desktop and the database.** Open **Containers** and show the running `cti-mongo-labs` container. From your project PowerShell terminal, run:

```powershell
docker compose -f docker-compose-labs.yml ps
docker exec cti-mongo-labs mongosh --quiet --eval "rs.status().members.map(m => ({name:m.name,state:m.stateStr}))"
```

**2. MongoDB data.** If your app database is using port 27019 as described in the README, show the stored educational guidance and message counts. These queries omit the embeddings and message text:

```powershell
docker exec cti-mongo-labs mongosh --quiet --eval "db.getSiblingDB('ctiSentinelDB').threat_knowledge.find({}, {_id:0,title:1,platform:1,stage:1}).limit(8).toArray()"
docker exec cti-mongo-labs mongosh --quiet --eval "db.getSiblingDB('ctiSentinelDB').ai_messages.countDocuments({provider:'openai'})"
```

For MongoDB Compass, connect to `mongodb://127.0.0.1:27019/?directConnection=true` and open **ctiSentinelDB → threat_knowledge**. If your app uses the separate MongoDB on port 27017, connect Compass to that app instance for chat data. Chapter 1–6 runners clean up temporary collections. Their returned result is the evidence for those runs.

**3. AI assistant.** Show the OpenAI model label. Choose **Windows → Active** and ask “How should I contain suspected Windows ransomware?” Open a source link from the response. Explain the flow: browser to Flask, embeddings to find matching MongoDB records, then retrieved excerpts to OpenAI for the answer.

**4. MongoDB labs.** Use the README table to explain all chapters. Good live examples are 3.1 for a nested query, 5.2 for a join, 6.1 for execution statistics, 10.1 for a committed transfer and a rollback, 17.2 for a vector simulation, and 18.2 for the report. Show the result for each. Lab 10.1 leaves test account and transfer records in the isolated database:

```powershell
docker exec cti-mongo-labs mongosh --quiet --eval "db.getSiblingDB('cti_sentinel_labs_sandbox').getCollection('lab10_1_accounts').find({}, {_id:0}).limit(5).toArray()"
```

**5. Dockerized app.** If your faculty member wants the complete chat stack, use the Docker chat instructions in the README. Show `docker compose -f docker-compose.app.yml ps` and open **http://localhost:5000**. Practice the mode switch before the presentation.

## If the demo fails

- **OpenAI setup required:** Confirm `AI_PROVIDER=openai` and the key exist in `.env`, then restart Flask. HTTP 401 generally indicates an authentication problem. HTTP 429 can indicate a request rate or quota limit.
- **No relevant threat guidance:** Run ingestion with the same provider and embedding model configured for the chat server. Check that the ingestion output says it indexed eight chunks.
- **Database operation failed:** Confirm Docker is running, the lab replica set is writable, and the lab URI points to port 27019. Check the backend terminal for errors. Keep credentials out of screenshots.
- **Port already in use:** Stop the previous Flask or Vite process before relaunching that service. Do not run the Windows Flask process and the Docker chat service on port 5000 at the same time.
