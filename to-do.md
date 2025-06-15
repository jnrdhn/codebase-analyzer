
#### **Step 4: Add a License**

Create a file named `LICENSE` in the root directory and paste the text of the MIT License into it. You can get the text here: [https://opensource.org/licenses/MIT](https://opensource.org/licenses/MIT) (just replace `[year]` and `[fullname]` with your info).

#### **Step 5: Push to GitHub**

1.  Go to [GitHub](https://github.com) and create a new, public repository (e.g., `codebase-analyzer`). Do **not** initialize it with a README or .gitignore.
2.  In your local terminal, in the project root:
    ```bash
    git init -b main
    git add .
    git commit -m "Initial commit: Full application structure"
    git remote add origin https://github.com/your-username/codebase-analyzer.git
    git push -u origin main
    ```

**Your project is now open-source!**

---

### **Part 2: Free Hosting & Deployment**

We will use two best-in-class services with excellent free tiers: **Vercel** for the frontend and **Render** for the entire backend.

#### **Step 1: Deploy the Frontend to Vercel**

1.  Go to [Vercel.com](https://vercel.com) and sign up with your GitHub account.
2.  Click "Add New..." -> "Project".
3.  Select your `codebase-analyzer` repository.
4.  Vercel will ask to "Configure Project". **This is important.**
    *   **Root Directory:** Change this to `frontend`.
    *   Vercel should automatically detect it's a Vite project. The build command (`npm run build`) and output directory (`dist`) should be correct.
5.  Expand the "Environment Variables" section.
    *   Add a new variable:
        *   **Name:** `VITE_API_BASE_URL`
        *   **Value:** `[Your Render backend URL - We'll get this in the next step]`
6.  Click **Deploy**. Vercel will build and deploy your React app.

#### **Step 2: Deploy the Backend to Render**

Render is perfect for this because it can host a web service, a background worker, a PostgreSQL DB, and Redis all for free and link them together.

1.  Go to [Render.com](https://render.com) and sign up with your GitHub account.
2.  On your Dashboard, click "New +" and we will add four services.

    **A. Add the PostgreSQL Database:**
    *   Click "New PostgreSQL".
    *   Give it a name (e.g., `codebase-db`).
    *   Select the "Free" plan.
    *   Click "Create Database". Render will give you a `DATABASE_URL` (Internal Connection String). Copy it.

    **B. Add the Redis Instance:**
    *   Click "New Redis".
    *   Give it a name (e.g., `codebase-redis`).
    *   Select the "Free" plan.
    *   Click "Create Redis". Render will give you a `REDIS_URL`. Copy it.

    **C. Add the FastAPI Web Service:**
    *   Click "New Web Service".
    *   Connect your `codebase-analyzer` GitHub repository.
    *   Give it a name (e.g., `codebase-api`).
    *   **Root Directory:** Leave this blank (it's the root).
    *   **Environment:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
    *   Select the "Free" plan.
    *   Expand "Advanced" -> "Environment Variables":
        *   Click "Add Secret File" and upload your Google API key JSON if you have one, or click "Add Environment Variable":
            *   `GOOGLE_API_KEY`: `your_gemini_key`
            *   `DATABASE_URL`: Paste the URL from your Render PostgreSQL DB.
            *   `REDIS_URL`: Paste the URL from your Render Redis instance.
    *   Click "Create Web Service". Render will start deploying. Once it's live, it will have a public URL like `https://codebase-api.onrender.com`. **This is the URL you need for Vercel.**

    **D. Add the Celery Background Worker:**
    *   Click "New Background Worker".
    *   Connect the same GitHub repository.
    *   Give it a name (e.g., `codebase-worker`).
    *   **Build Command and Start Command are the same as the web service initially.** Change the **Start Command** to:
        `celery -A app.core.celery_app worker --loglevel=info`
    *   Select the "Free" plan.
    *   Add the **exact same three environment variables** (`GOOGLE_API_KEY`, `DATABASE_URL`, `REDIS_URL`) as you did for the web service.
    *   Click "Create Background Worker".

#### **Step 3: Connect Frontend to Backend**

1.  Go back to your Vercel project dashboard.
2.  Go to Settings -> Environment Variables.
3.  Edit `VITE_API_BASE_URL` and paste in your Render API's public URL (e.g., `https://codebase-api.onrender.com`).
4.  Go to the "Deployments" tab in Vercel and trigger a new deployment to apply the new environment variable.

**You are now live!** Your project is fully deployed, open-source, and ready to share.

---

### **Part 3: Future Goal - Rate Limiting**

When you're ready, adding rate limiting is a great way to protect your API from abuse (and protect your API key costs).

1.  **Install `slowapi`:** Add `slowapi` to your `requirements.txt`.
2.  **Update `app/main.py`:**

    ```python
    # app/main.py
    from fastapi import FastAPI, Depends, HTTPException, Request
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    # ... other imports ...

    # Create a limiter that uses the client's IP address as the key
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI(...)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ... your CORS middleware ...

    @app.post("/analyze/", ...,)
    @limiter.limit("5/minute") # Example: 5 requests per minute per IP
    def create_analysis_job(request: Request, job_request: ..., db: ...):
        # ... your code ...

    @app.get("/jobs/{job_id}", ...)
    @limiter.limit("30/minute") # Allow more frequent status checks
    def get_job_status(request: Request, job_id: int, db: ...):
        # ... your code ...
    ```
    This adds a simple but effective layer of protection. Commit and push this change, and Render will automatically redeploy your API with the new feature.