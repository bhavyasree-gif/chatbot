"""Index small educational scenarios for local defensive threat chat."""
from pymongo import ReplaceOne

from backend.config.connection import get_db
from backend.services.threat_knowledge import embed, embedding_model

WINDOWS = "https://learn.microsoft.com/en-us/windows/security/operating-system-security/"
LINUX = "https://ubuntu.com/security/notices"
CISA = "https://www.cisa.gov/stopransomware/ransomware-guide"

# All records are educational scenarios, with official guidance linked separately.
RECORDS = [
    ("Windows", "Anticipated", "Outdated Windows endpoints",
     "Inventory supported Windows versions and enable automatic security updates. Review pending updates and test backup restoration before an incident.", WINDOWS),
    ("Windows", "Active", "Suspected ransomware on Windows",
     "If encryption or a ransom note is confirmed, coordinate with incident response, isolate the affected endpoint from the network, preserve evidence, and use a clean device for communications. Restore only after containment and verification.", CISA),
    ("Windows", "Evolving", "Ransomware scope is still changing",
     "Reassess affected accounts and hosts as new alerts arrive. Correlate endpoint, access, and backup logs. Coordinate containment with incident response and record the evidence and time behind each update.", CISA),
    ("Windows", "Resolved", "Recovery after ransomware containment",
     "Validate clean backups, restore to a trusted environment, rotate credentials through approved procedures, and monitor for recurrence. Record the closure criteria and any unresolved findings.", CISA),
    ("Linux", "Anticipated", "Unpatched Ubuntu packages",
     "Record the release and installed package versions. Check applicable Ubuntu Security Notices and plan upgrades through trusted repositories. Verify restart requirements before the maintenance window.", LINUX),
    ("Linux", "Active", "Suspected ransomware on Linux",
     "Coordinate with incident response. Isolate affected hosts where appropriate, preserve logs and disk evidence, and confirm backups are protected before recovery.", CISA),
    ("Linux", "Evolving", "New Ubuntu advisory affects installed software",
     "Check the latest advisory against the exact release and installed package version. Track revised fixed versions and update plans as the advisory changes. Escalate discrepancies to the system owner.", LINUX),
    ("Linux", "Resolved", "Ubuntu security update verification",
     "Compare installed versions with the fixed versions in the applicable security notice. Confirm any restart has completed and check service health. Record the advisory and verification time.", LINUX),
]


def main():
    chunks = []
    for platform, stage, title, text, url in RECORDS:
        words = text.split()
        for offset in range(0, len(words), 120):
            chunks.append({"_id": f"{platform}/{stage}/{offset}", "platform": platform,
                           "stage": stage, "title": title, "text": " ".join(words[offset:offset + 120]),
                           "url": url, "embedding_model": embedding_model()})
    vectors = embed([f"{row['title']} {row['text']}" for row in chunks])
    knowledge = get_db().threat_knowledge
    knowledge.create_index([("platform", 1), ("stage", 1), ("embedding_model", 1)])
    knowledge.bulk_write([ReplaceOne({"_id": row["_id"]}, {**row, "embedding": vector}, upsert=True)
                          for row, vector in zip(chunks, vectors)])
    print(f"Indexed {len(chunks)} defensive guidance chunks.")


if __name__ == "__main__":
    main()
