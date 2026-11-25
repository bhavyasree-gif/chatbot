import { useEffect, useState } from "react";
import { api } from "./api.js";

export default function HostScan() {
  const [status, setStatus] = useState(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/host-scan/status").then(setStatus).catch(e => setError(e.message)); }, []);
  const run = async () => {
    setBusy(true); setError(""); setReport(null);
    try { setReport(await api("/host-scan", { method: "POST", headers: { "X-Scan-Token": status.token }, body: { consent: true } })); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = "cti-windows-security-report.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <section>
    <div className="page-heading"><div><div className="eyebrow">LOCAL COMPUTER / SECURITY POSTURE</div><h1>Computer security scan</h1><p>Check Windows Defender, firewall, system drive encryption, UAC, and update history.</p></div></div>
    <div className="host-scan-card">
      <p>This checks the Windows computer running the Python backend. Each scan takes up to about 75 seconds. Personal files are not read. Results stay in this page until you leave or download them. Nothing is sent to an AI provider.</p>
      {status && !status.enabled && <p><strong>Enable scanning first.</strong> In the terminal used to start the backend, run <code>$env:ENABLE_HOST_SCAN="1"</code>, then restart the backend and refresh this page.</p>}
      {status && !status.supported && <p><strong>Windows backend required.</strong> Run Python directly on your Windows laptop. A Docker or Linux backend checks its own environment and cannot inspect Windows.</p>}
      <label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={busy}/> I authorize these read-only security checks on this computer.</label>
      <p><button className="quiet-btn" disabled={!consent || !status?.enabled || !status?.supported || busy} onClick={run}>{busy ? "Checking Windows security…" : "Scan this computer"}</button></p>
      {error && <p role="alert">{error}</p>}
    </div>
    {report && <div aria-live="polite">
      <div className="page-heading"><div><h2>Scan results</h2><p>{new Date(report.scanned_at).toLocaleString()} · {report.summary.pass} passed · {report.summary.warning} need review · {report.summary.unknown} unavailable</p></div><button className="quiet-btn" onClick={download}>Download report</button></div>
      <p>{report.limitations}</p>
      {report.findings.map(f => <article className="host-scan-card" key={f.id}><h3>{f.title} · {f.status === "pass" ? "Passed check" : f.status === "warning" ? "Review recommended" : "Unavailable"}</h3><p>{f.evidence}</p><p><strong>Next step</strong> {f.guidance}</p></article>)}
      <p>Review each recommendation before changing settings. This version does not apply fixes automatically.</p>
    </div>}
  </section>;
}
