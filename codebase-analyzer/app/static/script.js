document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("analysis-form");
    const repoUrlInput = document.getElementById("repo-url");
    const submitBtn = document.getElementById("submit-btn");
    const loadingDiv = document.getElementById("loading");
    const pollingStatus = document.getElementById("polling-status");
    const reportDiv = document.getElementById("report");

    const showdownConverter = new showdown.Converter();

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const repoUrl = repoUrlInput.value;
        if (!repoUrl) return;

        // --- UI State: Start Loading ---
        submitBtn.disabled = true;
        submitBtn.innerText = "Analyzing...";
        loadingDiv.classList.remove("hidden");
        reportDiv.innerHTML = "";

        try {
            // 1. Submit the job
            const response = await fetch("/analyze/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ github_url: repoUrl }),
            });

            if (!response.ok) {
                throw new Error("Failed to start analysis job.");
            }

            const job = await response.json();
            
            // 2. Start polling for the result
            pollForJobResult(job.id);

        } catch (error) {
            reportDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            resetUI();
        }
    });

    async function pollForJobResult(jobId) {
        pollingStatus.innerText = "Job submitted. Waiting for worker to start...";
        
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/jobs/${jobId}`);
                if (!response.ok) {
                    // Stop polling if job not found or server error
                    clearInterval(interval);
                    reportDiv.innerHTML = `<p style="color: red;">Error fetching job status.</p>`;
                    resetUI();
                    return;
                }

                const job = await response.json();
                pollingStatus.innerText = `Current status: ${job.status}`;

                if (job.status === "COMPLETE") {
                    clearInterval(interval);
                    pollingStatus.innerText = "Analysis complete!";
                    displayReport(job.report_content);
                    resetUI();
                } else if (job.status === "FAILED") {
                    clearInterval(interval);
                    reportDiv.innerHTML = `<p style="color: red;">Analysis Failed:</p><pre>${job.report_content}</pre>`;
                    resetUI();
                }
                // If status is PENDING or RUNNING, the loop continues
            } catch (error) {
                clearInterval(interval);
                reportDiv.innerHTML = `<p style="color: red;">Polling Error: ${error.message}</p>`;
                resetUI();
            }
        }, 5000); // Poll every 5 seconds
    }

    function displayReport(markdownContent) {
        // --- THIS IS THE FIX ---
        // 1. First, convert the raw markdown string into an HTML string.
        const htmlContent = showdownConverter.makeHtml(markdownContent);
        
        // 2. Hide the loading spinner.
        loadingDiv.classList.add("hidden");
        
        // 3. Now, insert the fully rendered HTML directly into the report div.
        reportDiv.innerHTML = htmlContent;
    }

    function resetUI() {
        submitBtn.disabled = false;
        submitBtn.innerText = "Analyze";
    }
});