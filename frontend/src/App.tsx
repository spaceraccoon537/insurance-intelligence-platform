import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  analyzeClaim,
  askQuestion,
  comparePolicies,
  deleteDocument,
  getHealth,
  listDocuments,
  uploadDocument,
  type ClaimAnalysisResponse,
  type ComparisonResponse,
  type DocumentResponse,
  type QuestionResponse,
  type SourceCitation,
} from "./api/client";

type Tab = "documents" | "questions" | "comparison" | "claims";

function citationsLabel(citations: SourceCitation[]): string {
  return citations
    .map((citation) => {
      const location = citation.page_number
        ? `p. ${citation.page_number}`
        : citation.section_title || "document";
      return `${citation.filename} · ${location}`;
    })
    .join("; ");
}

function App() {
  const [tab, setTab] = useState<Tab>("documents");
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [connection, setConnection] = useState<"checking" | "connected" | "unavailable">("checking");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const [question, setQuestion] = useState("");
  const [questionIds, setQuestionIds] = useState<string[]>([]);
  const [strategy, setStrategy] = useState<"semantic" | "bm25" | "hybrid">("hybrid");
  const [questionResult, setQuestionResult] = useState<QuestionResponse | null>(null);

  const [comparisonIds, setComparisonIds] = useState<string[]>([]);
  const [focusAreas, setFocusAreas] = useState("");
  const [comparisonResult, setComparisonResult] = useState<ComparisonResponse | null>(null);

  const [policyId, setPolicyId] = useState("");
  const [claimIds, setClaimIds] = useState<string[]>([]);
  const [claimResult, setClaimResult] = useState<ClaimAnalysisResponse | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const refreshDocuments = useCallback(async (signal?: AbortSignal) => {
    const response = await listDocuments(signal);
    setDocuments(response.documents);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    void (async () => {
      try {
        await getHealth(controller.signal);
        setConnection("connected");
        await refreshDocuments(controller.signal);
      } catch (error) {
        if (controller.signal.aborted) return;
        setConnection("unavailable");
        setNotice(error instanceof Error ? error.message : "The local API could not be reached.");
      }
    })();
    return () => controller.abort();
  }, [refreshDocuments]);

  const toggleId = (
    id: string,
    values: string[],
    setter: (next: string[]) => void,
  ) => {
    setter(values.includes(id) ? values.filter((value) => value !== id) : [...values, id]);
  };

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!uploadFile) {
      setNotice("Choose a PDF or DOCX file to upload.");
      return;
    }
    if (!/\.(pdf|docx)$/i.test(uploadFile.name)) {
      setNotice("Only PDF and DOCX files are supported.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      await uploadDocument(uploadFile);
      await refreshDocuments();
      setUploadFile(null);
      setNotice("Document uploaded and indexed.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "The document upload failed.");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    setBusy(true);
    setNotice("");
    try {
      await deleteDocument(documentId);
      await refreshDocuments();
      setQuestionIds((ids) => ids.filter((id) => id !== documentId));
      setComparisonIds((ids) => ids.filter((id) => id !== documentId));
      setClaimIds((ids) => ids.filter((id) => id !== documentId));
      if (policyId === documentId) setPolicyId("");
      setNotice("Document deleted.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "The document could not be deleted.");
    } finally {
      setBusy(false);
    }
  };

  const handleQuestion = async (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) {
      setNotice("Enter a question.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      setQuestionResult(await askQuestion(question.trim(), questionIds, strategy));
    } catch (error) {
      setQuestionResult(null);
      setNotice(error instanceof Error ? error.message : "The question could not be answered.");
    } finally {
      setBusy(false);
    }
  };

  const runComparison = async (event: FormEvent) => {
    event.preventDefault();
    if (comparisonIds.length < 2) {
      setNotice("Select at least two policy documents.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      const areas = focusAreas
        .split(",")
        .map((area) => area.trim())
        .filter(Boolean)
        .slice(0, 20);
      setComparisonResult(await comparePolicies(comparisonIds, areas));
    } catch (error) {
      setComparisonResult(null);
      setNotice(error instanceof Error ? error.message : "The comparison could not be created.");
    } finally {
      setBusy(false);
    }
  };

  const handleClaim = async (event: FormEvent) => {
    event.preventDefault();
    if (!policyId) {
      setNotice("Select a policy document.");
      return;
    }
    if (!claimIds.length) {
      setNotice("Select at least one claim document.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      setClaimResult(await analyzeClaim(policyId, claimIds));
    } catch (error) {
      setClaimResult(null);
      setNotice(error instanceof Error ? error.message : "The claim could not be analyzed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="workspace">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Insurance Intelligence Platform home">
          <span className="brand-mark" aria-hidden="true">I</span>
          <span>Insurance Intelligence</span>
        </a>
        <span className={`status-badge status-${connection}`}>
          <span aria-hidden="true" />
          {connection === "connected" ? "Local API connected" : connection === "checking" ? "Checking API" : "API unavailable"}
        </span>
      </header>

      <nav className="tabs" aria-label="Workspace tools">
        {([
          ["documents", "Documents"],
          ["questions", "Ask"],
          ["comparison", "Compare"],
          ["claims", "Claim review"],
        ] as [Tab, string][]).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={tab === value ? "tab active" : "tab"}
            onClick={() => setTab(value)}
            aria-current={tab === value ? "page" : undefined}
          >
            {label}
          </button>
        ))}
      </nav>

      {notice && (
        <div className="notice" role="alert">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")} aria-label="Dismiss message">×</button>
        </div>
      )}

      {tab === "documents" && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">DOCUMENT LIBRARY</p>
              <h1>Policy documents</h1>
            </div>
            <form className="upload-form" onSubmit={handleUpload}>
              <label className="file-control">
                <input
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                  disabled={busy}
                />
                <span>{uploadFile?.name ?? "Choose PDF or DOCX"}</span>
              </label>
              <button className="primary-button" type="submit" disabled={busy}>Upload</button>
            </form>
          </div>

          {documents.length === 0 ? (
            <div className="empty-state">
              <strong>No documents yet</strong>
              <p>Upload a synthetic PDF or DOCX to begin.</p>
            </div>
          ) : (
            <div className="document-list">
              {documents.map((document) => (
                <article className="document-row" key={document.document_id}>
                  <div className="document-icon" aria-hidden="true">PDF</div>
                  <div className="document-meta">
                    <strong>{document.filename}</strong>
                    <span>
                      {Math.max(1, Math.round(document.size_bytes / 1024))} KiB
                      {document.page_count ? ` · ${document.page_count} pages` : ""}
                    </span>
                  </div>
                  <span className="ready-label">{document.status}</span>
                  <button
                    className="delete-button"
                    type="button"
                    disabled={busy}
                    onClick={() => void handleDelete(document.document_id)}
                  >
                    Delete
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "questions" && (
        <section className="panel split-panel">
          <form className="tool-form" onSubmit={handleQuestion}>
            <p className="eyebrow">GROUNDED ANSWERS</p>
            <h1>Ask a policy question</h1>
            <label>
              Question
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                maxLength={4000}
                placeholder="What is excluded from flood coverage?"
              />
            </label>
            <label>
              Retrieval strategy
              <select value={strategy} onChange={(event) => setStrategy(event.target.value as typeof strategy)}>
                <option value="hybrid">Hybrid</option>
                <option value="semantic">Semantic</option>
                <option value="bm25">BM25</option>
              </select>
            </label>
            <fieldset>
              <legend>Documents <span>(leave empty to search all)</span></legend>
              {documents.map((document) => (
                <label className="check-row" key={document.document_id}>
                  <input
                    type="checkbox"
                    checked={questionIds.includes(document.document_id)}
                    onChange={() => toggleId(document.document_id, questionIds, setQuestionIds)}
                  />
                  <span>{document.filename}</span>
                </label>
              ))}
            </fieldset>
            <button className="primary-button" type="submit" disabled={busy}>Find answer</button>
          </form>
          <div className="result-pane">
            {!questionResult ? (
              <div className="empty-state compact">Answers and citations will appear here.</div>
            ) : (
              <>
                <div className="answer-card">
                  <span className="result-label">ANSWER</span>
                  <p>{questionResult.answer}</p>
                </div>
                <h2>Sources</h2>
                {questionResult.citations.map((citation) => (
                  <article className="citation" key={citation.chunk_id}>
                    <strong>{citation.filename}</strong>
                    <span>{citation.page_number ? `Page ${citation.page_number}` : citation.section_title || "Source excerpt"}</span>
                    <p>{citation.excerpt}</p>
                  </article>
                ))}
              </>
            )}
          </div>
        </section>
      )}

      {tab === "comparison" && (
        <section className="panel">
          <form className="inline-form" onSubmit={runComparison}>
            <div>
              <p className="eyebrow">POLICY COMPARISON</p>
              <h1>Compare coverage</h1>
            </div>
            <fieldset>
              <legend>Select at least two policies</legend>
              {documents.map((document) => (
                <label className="check-row" key={document.document_id}>
                  <input
                    type="checkbox"
                    checked={comparisonIds.includes(document.document_id)}
                    onChange={() => toggleId(document.document_id, comparisonIds, setComparisonIds)}
                  />
                  <span>{document.filename}</span>
                </label>
              ))}
            </fieldset>
            <label>
              Focus areas <span>(comma separated)</span>
              <input
                value={focusAreas}
                onChange={(event) => setFocusAreas(event.target.value)}
                placeholder="coverage, deductible, exclusions"
                maxLength={500}
              />
            </label>
            <button className="primary-button" type="submit" disabled={busy}>Compare documents</button>
          </form>
          {comparisonResult && (
            <div className="comparison-results">
              <p className="summary">{comparisonResult.summary}</p>
              {comparisonResult.dimensions.map((dimension) => (
                <article className="dimension" key={dimension.name}>
                  <h2>{dimension.name}</h2>
                  {dimension.values.map((value) => {
                    const filename = documents.find((document) => document.document_id === value.document_id)?.filename || value.document_id;
                    return (
                      <div className="dimension-value" key={value.document_id}>
                        <strong>{filename}</strong>
                        <p>{value.value}</p>
                        {value.citations.length > 0 && <small>{citationsLabel(value.citations)}</small>}
                      </div>
                    );
                  })}
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "claims" && (
        <section className="panel split-panel">
          <form className="tool-form" onSubmit={handleClaim}>
            <p className="eyebrow">CLAIM DOCUMENT REVIEW</p>
            <h1>Check claim completeness</h1>
            <label>
              Policy document
              <select value={policyId} onChange={(event) => setPolicyId(event.target.value)}>
                <option value="">Select a policy</option>
                {documents.map((document) => (
                  <option value={document.document_id} key={document.document_id}>{document.filename}</option>
                ))}
              </select>
            </label>
            <fieldset>
              <legend>Claim documents</legend>
              {documents.map((document) => (
                <label className="check-row" key={document.document_id}>
                  <input
                    type="checkbox"
                    checked={claimIds.includes(document.document_id)}
                    onChange={() => toggleId(document.document_id, claimIds, setClaimIds)}
                  />
                  <span>{document.filename}</span>
                </label>
              ))}
            </fieldset>
            <button className="primary-button" type="submit" disabled={busy}>Analyze claim</button>
          </form>
          <div className="result-pane">
            {!claimResult ? (
              <div className="empty-state compact">Review findings will appear here.</div>
            ) : (
              <>
                <div className="answer-card">
                  <span className="result-label">POTENTIALLY MISSING DOCUMENTS</span>
                  {claimResult.potentially_missing_document_types.length ? (
                    <ul>
                      {claimResult.potentially_missing_document_types.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  ) : <p>None identified from the submitted text.</p>}
                </div>
                {claimResult.findings.map((finding, index) => (
                  <article className={`finding finding-${finding.severity}`} key={`${finding.title}-${index}`}>
                    <span>{finding.severity.replaceAll("_", " ")}</span>
                    <h2>{finding.title}</h2>
                    <p>{finding.explanation}</p>
                    {finding.citations.map((citation) => (
                      <small key={citation.chunk_id}>{citationsLabel([citation])}</small>
                    ))}
                  </article>
                ))}
                <p className="disclaimer"><strong>Notice:</strong> {claimResult.disclaimer}</p>
              </>
            )}
          </div>
        </section>
      )}

      <footer className="footer">
        <span>Built for local-first document analysis.</span>
        <span>Use synthetic documents for demos.</span>
      </footer>
    </main>
  );
}

export default App;
