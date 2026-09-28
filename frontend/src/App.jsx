import { useEffect, useState } from "react";
import { getHealth } from "./services/api";

function App() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function checkBackend() {
      try {
        const data = await getHealth();
        setHealth(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    checkBackend();
  }, []);

  return (
    <div style={{ padding: "40px", fontFamily: "Arial" }}>
      <h1>DBA AI Agent</h1>

      <h2>Backend Connection</h2>

      {loading && <p>Connecting to FastAPI...</p>}

      {error && (
        <div>
          <p>❌ Backend connection failed</p>
          <pre>{error}</pre>
        </div>
      )}

      {health && (
        <div>
          <p>✅ FastAPI backend connected</p>

          <pre>
            {JSON.stringify(health, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default App;