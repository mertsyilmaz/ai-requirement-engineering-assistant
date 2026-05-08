import { cloneElement, useState } from "react";
import "./App.css";

function App() {
  const [text, setText] = useState("");
  const [provider, setProvider] = useState("mock");
  const [analysisVersion, setAnalysisVersion] = useState("v1");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPromptModal, setShowPromptModal] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    setShowPromptModal(false);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/requirements/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text,
          provider,
          analysisVersion
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Request failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const preAnalysis = result?.preAnalysis;
  const hasPrompt = Boolean(result?.promptUsed);

  return (
    <div className="page">
      <div className="app-frame">
        <header className="topbar">
          <h1>AI Requirement Engineering Assistant</h1>
          <div className="topbar-actions">
            <button type="button" title="Help">?</button>
            <button type="button" title="Settings">*</button>
          </div>
        </header>

        <main className="workspace">
          <section className="composer">
            {hasPrompt && (
              <button
                className="prompt-launch"
                type="button"
                onClick={() => setShowPromptModal(true)}
                title="View generated prompt"
              >
                <span className="file-corner" />
                <span>&lt;/&gt;</span>
              </button>
            )}

            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              className="composer-input"
              placeholder="Enter a software requirement in natural language..."
            />

            <div className="composer-controls">
              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
              >
                <option value="mock">Provider: Mock</option>
                <option value="gemini">Provider: Gemini</option>
              </select>

              <select
                value={analysisVersion}
                onChange={(event) => setAnalysisVersion(event.target.value)}
              >
                <option value="v1">Version: V1</option>
                <option value="v2">Version: V2</option>
              </select>

              <button
                type="button"
                className="analyze-button"
                onClick={handleAnalyze}
                disabled={loading || !text.trim()}
              >
                {loading ? "Analyzing..." : "Analyze"}
              </button>
            </div>
          </section>

          {error && (
            <div className="error-banner">
              <strong>Error:</strong> {error}
            </div>
          )}

          {result && (
            <section className="content-grid">
              <div className="result-stack">
                <ResultCard icon="PI" tone="blue" title="Provider Info">
                  <div className="provider-info-row">
                    <div className="meta-row">
                      <span><strong>Provider:</strong> <b>{result.providerUsed}</b></span>
                      <span><strong>Version:</strong> <b>{analysisVersion.toUpperCase()}</b></span>
                      <span><strong>Fallback:</strong> <b>{result.isFallback ? "Yes" : "No"}</b></span>
                    </div>
                    {getFriendlyWarning(result) && (
                      <div className="provider-warning">
                        {getFriendlyWarning(result)}
                      </div>
                    )}
                  </div>
                </ResultCard>

                <ResultCard icon="US" tone="green" title="User Story">
                  <p>{result.userStory}</p>
                </ResultCard>

                <ResultCard icon="RT" tone="purple" title="Requirement Type">
                  <p className="inline-value">{result.requirementType}</p>
                </ResultCard>

                <ResultCard
                  icon="!"
                  tone="orange"
                  title="Ambiguities"
                  count={result.ambiguities?.length || 0}
                >
                  <BulletList
                    items={result.ambiguities}
                    emptyText="No ambiguities found."
                    renderItem={(item) => `${item.phrase}: ${item.reason}`}
                  />
                </ResultCard>

                <ResultCard
                  icon="S"
                  tone="yellow"
                  title="Suggestions"
                  count={result.suggestions?.length || 0}
                >
                  <BulletList
                    items={result.suggestions}
                    emptyText="No suggestions available."
                    renderItem={(item) => `${item.originalPart} -> ${item.suggestedPart}. ${item.reason}`}
                  />
                </ResultCard>

                <ResultCard icon="IT" tone="cyan" title="Improved Text">
                  <p>{result.improvedText}</p>
                </ResultCard>

                <ResultCard
                  icon="ALT"
                  tone="blue"
                  title="Improved Text Options"
                  count={result.improvedTextOptions?.length || 0}
                >
                  <OptionList items={result.improvedTextOptions} />
                </ResultCard>
              </div>

              <aside className="side-panel">
                <h2>Pre-analysis</h2>

                {preAnalysis ? (
                  <>
                    <PreAnalysisGroup title="Pre-analysis Findings" tone="findings">
                      <SideSection
                        icon="?"
                        title="Candidate Ambiguities"
                        count={preAnalysis.ambiguityCandidates?.length || 0}
                        tone="blue"
                      >
                        <MiniList
                          items={preAnalysis.ambiguityCandidates}
                          renderItem={(item) => item.matchedText}
                        />
                      </SideSection>

                      <SideSection
                        icon="OK"
                        title="Confirmed Ambiguities"
                        count={preAnalysis.confirmedAmbiguities?.length || 0}
                        tone="green"
                      >
                        <MiniList
                          items={preAnalysis.confirmedAmbiguities}
                          renderItem={(item) => item.matchedText}
                        />
                      </SideSection>

                      <SideSection
                        icon="x"
                        title="Rejected Candidates"
                        count={preAnalysis.rejectedAmbiguityCandidates?.length || 0}
                        tone="red"
                      >
                        <MiniList
                          items={preAnalysis.rejectedAmbiguityCandidates}
                          renderItem={(item) =>
                            `${item.matchedText}${item.supportingExpression ? ` (${item.supportingExpression})` : ""}`
                          }
                        />
                      </SideSection>

                      <SideSection
                        icon="Q"
                        title="Reference Ambiguities"
                        count={preAnalysis.referenceAmbiguities?.length || 0}
                        tone="purple"
                      >
                        <MiniList
                          items={preAnalysis.referenceAmbiguities}
                          renderItem={(item) => `${item.phrase} (${item.category})`}
                        />
                      </SideSection>

                      <SideSection
                        icon="G"
                        title="Measurement Ambiguities"
                        count={preAnalysis.measurementAmbiguities?.length || 0}
                        tone="orange"
                      >
                        <MiniList
                          items={preAnalysis.measurementAmbiguities}
                          renderItem={(item) => `${item.phrase} (${item.missingDimension})`}
                        />
                      </SideSection>
                    </PreAnalysisGroup>

                    <PreAnalysisGroup title="Context Observations" tone="context">
                      <SideSection
                        icon="MC"
                        title="Measurement Contexts"
                        count={preAnalysis.measurementContexts?.length || 0}
                        tone="yellow"
                      >
                        <MiniList
                          items={preAnalysis.measurementContexts}
                          renderItem={renderMeasurementContext}
                        />
                      </SideSection>

                      <SideSection
                        icon="SV"
                        title="Semantic Findings"
                        count={preAnalysis.semanticFindings?.length || 0}
                        tone="blue"
                      >
                        <MiniList
                          items={preAnalysis.semanticFindings}
                          renderItem={(item) => `${item.phrase} (${item.decision})`}
                        />
                      </SideSection>

                      <SideSection
                        icon="M"
                        title="Measurable Expressions"
                        count={preAnalysis.measurableExpressions?.length || 0}
                        tone="cyan"
                      >
                        <MiniList
                          items={preAnalysis.measurableExpressions}
                          renderItem={(item) => item.text}
                        />
                      </SideSection>
                    </PreAnalysisGroup>
                  </>
                ) : (
                  <SideSection icon="i" title="No Pre-analysis" count={0} tone="blue">
                    <p className="muted">Pre-analysis details are available for V2.</p>
                  </SideSection>
                )}
              </aside>
            </section>
          )}
        </main>

        {showPromptModal && (
          <div className="modal-backdrop" onClick={() => setShowPromptModal(false)}>
            <div className="prompt-modal" onClick={(event) => event.stopPropagation()}>
              <div className="modal-header">
                <h2>Generated Prompt</h2>
                <button type="button" onClick={() => setShowPromptModal(false)}>
                  x
                </button>
              </div>
              <div className="prompt-code">
                <pre>{withLineNumbers(result?.promptUsed || "")}</pre>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setShowPromptModal(false)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PreAnalysisGroup({ title, tone, children }) {
  return (
    <div className={`pre-analysis-group ${tone}`}>
      <div className="pre-analysis-group-title">{title}</div>
      {children}
    </div>
  );
}

function ResultCard({ icon, tone, title, count, children }) {
  return (
    <article className="result-card">
      <div className={`result-icon ${tone}`}>{icon}</div>
      <div className="result-body">
        <div className="card-title-row">
          <h3>{title}</h3>
          {typeof count === "number" && <span className={`count-badge ${tone}`}>{count}</span>}
        </div>
        {children}
      </div>
    </article>
  );
}

function renderMeasurementContext(item) {
  const details = [];

  if (item.percentageTarget && item.percentageSubject) {
    details.push(`${item.percentageTarget} -> ${item.percentageSubject}`);
  }

  if (item.loadContext) {
    details.push(`load: ${item.loadContext}`);
  }

  if (item.statisticalTarget) {
    details.push(`statistical: ${item.statisticalTarget}`);
  }

  if (item.measuredItem) {
    details.push(`measured: ${item.measuredItem}`);
  }

  if (item.nearbyAction) {
    details.push(`action: ${item.nearbyAction}`);
  }

  if (item.timeTarget) {
    details.push(`time: ${item.timeTarget}`);
  }

  if (item.condition) {
    details.push(`condition: ${item.condition}`);
  }

  return details.join("; ") || item.sentence;
}

function SideSection({ icon, title, count, tone, children }) {
  const [expanded, setExpanded] = useState(false);
  const hasHiddenItems = count > 3;

  return (
    <section className="side-section">
      <div className="side-title-row">
        <div className="side-title">
          <span className={`small-icon ${tone}`}>{icon}</span>
          <h3>{title}</h3>
        </div>
        <span className={`count-badge ${tone}`}>{count}</span>
      </div>
      {children?.type === MiniList
        ? cloneElement(children, { expanded, visibleLimit: 3 })
        : children}
      {hasHiddenItems && (
        <button
          className="view-link"
          type="button"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Show less" : "View all"}
        </button>
      )}
    </section>
  );
}


function BulletList({ items, emptyText, renderItem }) {
  if (!items || items.length === 0) {
    return <p className="muted">{emptyText}</p>;
  }

  return (
    <ul className="bullet-list">
      {items.map((item, index) => (
        <li key={index}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

function MiniList({ items, renderItem, expanded = true, visibleLimit = 3 }) {
  if (!items || items.length === 0) {
    return <p className="muted">No items.</p>;
  }

  const visibleItems = expanded ? items : items.slice(0, visibleLimit);

  return (
    <ul className="mini-list">
      {visibleItems.map((item, index) => (
        <li key={index}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

function OptionList({ items }) {
  const [expanded, setExpanded] = useState(false);

  if (!items || items.length === 0) {
    return <p className="muted">No improved text options available.</p>;
  }

  const visibleItems = expanded ? items : items.slice(0, 1);
  const hasHiddenItems = items.length > 1;

  return (
    <>
      <div className="option-list">
        {visibleItems.map((item, index) => (
          <div className="option-item" key={index}>
            <div className="option-label">{item.label}</div>
            <p>{item.text}</p>
            <small>{item.reason}</small>
          </div>
        ))}
      </div>
      {hasHiddenItems && (
        <button
          className="view-link"
          type="button"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Show less" : "View all"}
        </button>
      )}
    </>
  );
}

function getFriendlyWarning(result) {
  const warnings = result?.warnings || [];

  if (warnings.some((item) => item.toLowerCase().includes("gemini quota"))) {
    return "Gemini token/request limit reached. Mock response is shown.";
  }

  if (result?.isFallback) {
    return "Selected provider failed. Mock response is shown.";
  }

  return "";
}

function withLineNumbers(text) {
  return text
    .split("\n")
    .map((line, index) => `${String(index + 1).padStart(2, " ")}   ${line}`)
    .join("\n");
}

export default App;
