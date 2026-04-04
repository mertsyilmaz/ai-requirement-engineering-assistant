import { useState } from "react";

function App() {
  const [text, setText] = useState("");
  const [provider, setProvider] = useState("mock");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/requirements/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text,
          provider
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

  const cardStyle = {
    backgroundColor: "#f7f7f7",
    padding: "16px",
    borderRadius: "8px",
    marginTop: "16px",
    border: "1px solid #ddd"
  };

  return (
    <div style={{ padding: "30px", maxWidth: "1000px", margin: "0 auto" }}>
      <h1>AI Requirement Engineering Assistant</h1>

      <div style={{ marginTop: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Requirement Text
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          style={{ width: "100%", padding: "10px", fontSize: "16px" }}
          placeholder="Enter a software requirement..."
        />
      </div>

      <div style={{ marginTop: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Provider
        </label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          style={{ padding: "10px", fontSize: "16px" }}
        >
          <option value="mock">Mock</option>
          <option value="gemini">Gemini</option>
        </select>
      </div>

      <div style={{ marginTop: "20px" }}>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          style={{
            padding: "10px 20px",
            fontSize: "16px",
            cursor: "pointer"
          }}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: "20px", color: "red" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: "30px" }}>
          <h2>Analysis Result</h2>

          <div style={cardStyle}>
            <h3>Provider Info</h3>
            <p><strong>Provider Used:</strong> {result.providerUsed}</p>
            <p><strong>Fallback Used:</strong> {result.isFallback ? "Yes" : "No"}</p>
          </div>

          {result.warnings && result.warnings.length > 0 && (
            <div style={{ ...cardStyle, backgroundColor: "#fff8e1", border: "1px solid #f0c36d" }}>
              <h3>Warnings</h3>
              <ul>
                {result.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {result.errors && result.errors.length > 0 && (
            <div style={{ ...cardStyle, backgroundColor: "#fdecea", border: "1px solid #f5c2c0" }}>
              <h3>Errors</h3>
              <ul>
                {result.errors.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          <div style={cardStyle}>
            <h3>Original Text</h3>
            <p>{result.originalText}</p>
          </div>

          <div style={cardStyle}>
            <h3>User Story</h3>
            <p>{result.userStory}</p>
          </div>

          <div style={cardStyle}>
            <h3>Requirement Type</h3>
            <p>{result.requirementType}</p>
          </div>

          <div style={cardStyle}>
            <h3>Ambiguities</h3>
            {result.ambiguities && result.ambiguities.length > 0 ? (
              <ul>
                {result.ambiguities.map((item, index) => (
                  <li key={index} style={{ marginBottom: "10px" }}>
                    <strong>Phrase:</strong> {item.phrase} <br />
                    <strong>Reason:</strong> {item.reason} <br />
                    <strong>Severity:</strong> {item.severity}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No ambiguities found.</p>
            )}
          </div>

          <div style={cardStyle}>
            <h3>Suggestions</h3>
            {result.suggestions && result.suggestions.length > 0 ? (
              <ul>
                {result.suggestions.map((item, index) => (
                  <li key={index} style={{ marginBottom: "10px" }}>
                    <strong>Original Part:</strong> {item.originalPart} <br />
                    <strong>Suggested Part:</strong> {item.suggestedPart} <br />
                    <strong>Reason:</strong> {item.reason}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No suggestions available.</p>
            )}
          </div>

          <div style={cardStyle}>
            <h3>Improved Text</h3>
            <p>{result.improvedText}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;