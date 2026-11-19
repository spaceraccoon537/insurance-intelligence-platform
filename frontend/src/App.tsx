import { useCallback, useEffect, useState } from "react";

import { getHealth } from "./api/client";

type ConnectionState =
  | { status: "checking" }
  | { status: "connected"; version: string }
  | { status: "unavailable"; message: string };

function App() {
  const [connection, setConnection] = useState<ConnectionState>({ status: "checking" });

  const checkBackend = useCallback(async (signal?: AbortSignal) => {
    setConnection({ status: "checking" });

    try {
      const health = await getHealth(signal);
      setConnection({ status: "connected", version: health.api_version });
    } catch (error) {
      if (signal?.aborted) return;

      setConnection({
        status: "unavailable",
        message: error instanceof Error ? error.message : "The backend could not be reached.",
      });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void checkBackend(controller.signal);
    return () => controller.abort();
  }, [checkBackend]);

  return (
    <main className="workspace">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Insurance Intelligence Platform home">
          <span className="brand-mark" aria-hidden="true">I</span>
          <span>Insurance Intelligence</span>
        </a>
        <span className="local-badge">LOCAL WORKSPACE</span>
      </header>

      <section className="welcome" aria-labelledby="welcome-title">
        <p className="eyebrow">POLICY DOCUMENT WORKSPACE</p>
        <h1 id="welcome-title">Clarity for the fine print.</h1>
        <p className="intro">
          Search, understand, and compare insurance documents with answers grounded in their
          original clauses.
        </p>
        <div className={`connection connection-${connection.status}`} role="status">
          <span className="connection-dot" aria-hidden="true" />
          {connection.status === "checking" && <span>Checking local API…</span>}
          {connection.status === "connected" && (
            <span>Local API connected · {connection.version}</span>
          )}
          {connection.status === "unavailable" && (
            <>
              <span>{connection.message}</span>
              <button className="retry-button" onClick={() => void checkBackend()}>
                Retry
              </button>
            </>
          )}
        </div>
      </section>

      <section className="feature-grid" aria-label="Platform capabilities">
        <article className="feature-card">
          <span className="feature-number">01</span>
          <h2>Ask with evidence</h2>
          <p>Get policy answers linked to the clauses and pages they came from.</p>
          <span className="phase-label">COMING IN PHASE 3</span>
        </article>
        <article className="feature-card">
          <span className="feature-number">02</span>
          <h2>Compare coverage</h2>
          <p>Review benefits, exclusions, limits, and conditions across policies.</p>
          <span className="phase-label">COMING IN PHASE 5</span>
        </article>
        <article className="feature-card">
          <span className="feature-number">03</span>
          <h2>Review claim documents</h2>
          <p>Spot potentially missing information and clauses worth a closer look.</p>
          <span className="phase-label">COMING IN PHASE 5</span>
        </article>
      </section>

      <footer className="footer">
        <span>Built for local-first document analysis.</span>
        <span>Use synthetic documents for demos.</span>
      </footer>
    </main>
  );
}

export default App;
