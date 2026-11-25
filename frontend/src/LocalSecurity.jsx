import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

function localApi(path, options = {}) {
  return api("/local-security" + path, { ...options, headers: { "X-CTI-Local": "1" } });
}

export default function LocalSecurity() {
  const [images, setImages] = useState(null);
  const [imageError, setImageError] = useState("");
  const [loadingImages, setLoadingImages] = useState(false);
  const [file, setFile] = useState(null);
  const [scan, setScan] = useState(null);
  const [scanError, setScanError] = useState("");
  const [starting, setStarting] = useState(false);

  const loadImages = useCallback(async () => {
    setLoadingImages(true);
    setImageError("");
    try {
      setImages((await localApi("/images")).images);
    } catch (error) {
      setImages(null);
      setImageError(error.message);
    } finally {
      setLoadingImages(false);
    }
  }, []);

  useEffect(() => { loadImages(); }, [loadImages]);
  const running = scan?.status === "running";
  useEffect(() => {
    let active = true;
    async function update() {
      try {
        const result = await localApi("/scan");
        if (active) setScan(result);
      } catch (error) {
        if (active) setScanError(error.message);
      }
    }
    update();
    const timer = running ? setInterval(update, 2000) : null;
    return () => { active = false; clearInterval(timer); };
  }, [running]);

  async function startScan(kind) {
    setStarting(true);
    setScanError("");
    try {
      const body = kind === "file" ? new FormData() : undefined;
      if (body) body.append("file", file);
      setScan(await localApi("/scan/" + kind, { method: "POST", body }));
    } catch (error) {
      setScanError(error.message);
    } finally {
      setStarting(false);
    }
  }

  const busy = starting || running;
  return <>
    <div className="page-heading"><div><h1>Local security</h1><p>Scan with Microsoft Defender and inspect local Docker images.</p></div></div>
    <section className="notice">
      <h2>Microsoft Defender Antivirus</h2>
      <p>Quick Scan is suited to a live demo. Full Scan can take much longer. Windows may quarantine threats according to its settings.</p>
      <div className="lab-actions">
        <button className="action-primary" disabled={busy} onClick={() => startScan("quick")}>Quick scan laptop</button>
        <button className="quiet-btn" disabled={busy} onClick={() => startScan("full")}>Full scan laptop</button>
      </div>
      <div className="lab-actions">
        <label>File to scan (up to 50 MB) <input type="file" disabled={busy} onChange={event => setFile(event.target.files[0] ?? null)}/></label>
        <button className="quiet-btn" disabled={busy || !file} onClick={() => startScan("file")}>Scan file</button>
      </div>
      {scanError && <p role="alert">{scanError}</p>}
      {scan?.status && scan.status !== "idle" && <div role="status">
        <p><strong>{scan.filename || (scan.kind === "quick" ? "Quick scan" : "Full scan")}</strong> {running ? "in progress…" : scan.summary}</p>
        {scan.sha256 && <p>SHA-256 <code style={{ overflowWrap: "anywhere" }}>{scan.sha256}</code></p>}
        {scan.output && <details open={scan.status === "review"}><summary>Defender output</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{scan.output}</pre></details>}
      </div>}
    </section>
    <section className="notice">
      <h2>Docker images{images && ` (${images.length})`}</h2>
      <button className="quiet-btn" disabled={loadingImages} onClick={loadImages}>{loadingImages ? "Loading…" : "Refresh images"}</button>
      {imageError && <p role="alert">{imageError}</p>}
      {images?.length === 0 && <p>No images in the local Docker engine.</p>}
      {images?.length > 0 && <div style={{ overflowX: "auto" }}><table>
        <thead><tr><th>Repository</th><th>Tag</th><th>Image ID</th><th>Size</th></tr></thead>
        <tbody>{images.map(image => <tr key={JSON.stringify([image.Repository, image.Tag, image.ID])}>
          <td>{image.Repository}</td><td>{image.Tag}</td><td><code>{image.ID}</code></td><td>{image.Size}</td>
        </tr>)}</tbody>
      </table></div>}
    </section>
  </>;
}
