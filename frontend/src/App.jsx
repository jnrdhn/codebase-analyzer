import { useState, useEffect } from 'react';
import showdown from 'showdown';
import './App.css';

const API_BASE_URL = "http://localhost:8000"; // Your FastAPI server URL

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [job, setJob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // const showdownConverter = new showdown.Converter();
  const showdownConverter = new showdown.Converter({
    tables: true, // Enable table parsing
    simplifiedAutoLink: true, // Autolink URLs
    strikethrough: true, // Enable strikethrough text
    tasklists: true, // Enable tasklists
    ghCompatibleHeaderId: true, // Generate GitHub-compatible header IDs
    simpleLineBreaks: true, // Treat newlines as <br> tags
  });

  // This effect hook handles the polling logic
  useEffect(() => {
    // Don't do anything if there's no job to poll
    if (!job || job.status === "COMPLETE" || job.status === "FAILED") {
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/jobs/${job.id}`);
        if (!response.ok) {
          throw new Error("Failed to fetch job status.");
        }
        const updatedJob = await response.json();
        setJob(updatedJob); // Update the state with the latest job status

        // If the job is done, clear the interval
        if (updatedJob.status === "COMPLETE" || updatedJob.status === "FAILED") {
          clearInterval(intervalId);
          setIsLoading(false); // Stop the main loading state
        }
      } catch (err) {
        setError(err.message);
        clearInterval(intervalId);
        setIsLoading(false);
      }
    }, 5000); // Poll every 5 seconds

    // Cleanup function: This is crucial to prevent memory leaks!
    // React runs this when the component unmounts or dependencies change.
    return () => clearInterval(intervalId);

  }, [job]); // The dependency array: this effect runs whenever the 'job' state changes

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!repoUrl) return;

    // Reset state for a new submission
    setIsLoading(true);
    setJob(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_url: repoUrl }),
      });

      if (!response.ok) {
        throw new Error("Failed to start analysis job.");
      }
      const initialJob = await response.json();
      setJob(initialJob); // Kick off the polling by setting the job state
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  const renderReport = () => {
    if (!job || !job.report_content) return null;

    if (job.status === "FAILED") {
        return (
            <>
                <p style={{ color: "red" }}>Analysis Failed:</p>
                <pre>{job.report_content}</pre>
            </>
        )
    }

    let contentToRender = job.report_content;
    // Check for and remove the markdown code fence
    if (contentToRender.includes("```markdown")) {
        contentToRender = contentToRender
            .replace(/```markdown\n?/g, "") // Remove starting fence
            .replace(/```/g, "");             // Remove ending fence
    }

    // console.log("Raw content from API:", job.report_content);

    // Use dangerouslySetInnerHTML to render the HTML from markdown
    // This is safe here because we trust the output from our own backend/AI.
    const reportHtml = showdownConverter.makeHtml(contentToRender);
    console.log("HTML output from Showdown:", reportHtml); // Optional: see what showdown produces
    return <div dangerouslySetInnerHTML={{ __html: reportHtml }} />;
  }

  return (
    <div className="container">
      <header>
        <h1>AI Codebase Analyst</h1>
        <p>Enter a public GitHub repository URL to generate an AI-powered analysis.</p>
      </header>

      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/user/repo"
          required
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      <div id="results-container">
        {isLoading && (
            <div id="loading">
                <div className="spinner"></div>
                <p>Analyzing repository... This may take a few minutes.</p>
                <p id="polling-status">
                    {job ? `Current status: ${job.status}` : 'Submitting job...'}
                </p>
            </div>
        )}
        {error && <p style={{ color: 'red' }}>Error: {error}</p>}
        {job && job.status === "COMPLETE" && renderReport()}
        {job && job.status === "FAILED" && renderReport()}
      </div>
    </div>
  );
}

export default App;