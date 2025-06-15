# main_gemini.py - Phase 1: Autonomous Codebase Analyst Agent (CLI using Gemini)

import os
import sys
import argparse
import subprocess
import tempfile
from google import genai
from google.genai import types


# --- Configuration ---
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".php",
    ".html", ".css", ".scss", ".sql", ".sh"
}
TOP_K_FILES = 5
# Switch to a powerful Gemini model. 1.5 Flash is fast and cheap.
AI_MODEL = "gemini-1.5-flash"

# --- LLM Prompt Engineering ---
# The system prompt is now a "system_instruction" for Gemini, which is a more robust way
# to set the AI's persona and task.
SYSTEM_INSTRUCTION = """
You are an expert software engineering assistant. Your task is to analyze individual source code files and provide a concise, high-level summary.

When given the content of a file, respond in markdown format with the following structure:

### 1. Purpose
A brief, one-sentence summary of the file's primary role or responsibility.

### 2. Key Components
- **Function/Class/Component 1:** A short description of its purpose.
- **Function/Class/Component 2:** A short description of its purpose.
(List the most important components only)

### 3. Potential Complexities
A bulleted list of 1-3 potential challenges or complexities a new developer might face when working with this file (e.g., complex logic, external dependencies, non-obvious side effects).
"""

# --- Core Functions ---


def configure_gemini():
    """Configures the Gemini client with the API key from environment variables."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)
    # print(f"API key is set. {api_key}")
    return genai.Client(api_key=api_key)


def clone_repo(repo_url, temp_dir):
    """Clones a public GitHub repository into a temporary directory."""
    print(f"Cloning repository: {repo_url}...")
    try:
        subprocess.run(
            ["git", "clone", repo_url, temp_dir],
            check=True,
            capture_output=True,
            text=True
        )
        print("Repository cloned successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e.stderr}")
        sys.exit(1)


def find_top_k_files(repo_path):
    """Finds the top K largest files with supported extensions in the repository."""
    print(f"Analyzing repository structure to find top {TOP_K_FILES} files...")
    file_paths = []
    for root, _, files in os.walk(repo_path):
        if '.git' in root:
            continue
        for file in files:
            if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                full_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(full_path)
                    file_paths.append((full_path, size))
                except OSError:
                    continue

    file_paths.sort(key=lambda x: x[1], reverse=True)
    return [path for path, size in file_paths[:TOP_K_FILES]]


def get_code_summary(client, file_path, repo_path):
    """Reads a file's content and gets a summary from the Gemini model."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return f"Error reading file: {e}"

    # Truncate content if it's too large to prevent excessive API costs/errors
    if len(content) > 15000:
        content = content[:15000] + "\n... (file truncated)"

    try:

        # 1. Prepare the user prompt
        user_prompt = f"Analyze this file: `{os.path.relpath(file_path, repo_path)}`\n\n```\n{content}\n```"

        # 2. Call the API
        response = client.models.generate_content(
        model="gemini-2.0-flash", contents="Explain how AI works in a few words"
        )
        # 3. Parse and return the response
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            ),
        )

        # 4. Return the text content (Gemini's response object is simpler)
        return response.text
    except Exception as e:
        return f"Error calling Google Gemini API: {e}"


def generate_report(repo_url, report_content):
    """Saves the final analysis report to a markdown file."""
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    filename = f"report_gemini_{repo_name}.md"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n✅ Analysis complete! Report saved as: {filename}")


def main():
    """Main function to orchestrate the analysis."""
    parser = argparse.ArgumentParser(
        description="Autonomous Codebase Analyst Agent (Gemini Edition)")
    parser.add_argument(
        "repo_url", help="The URL of the public GitHub repository to analyze.")
    args = parser.parse_args()

    client = configure_gemini()

    repo_url = args.repo_url

    with tempfile.TemporaryDirectory() as temp_dir:
        clone_repo(repo_url, temp_dir)
        files_to_analyze = find_top_k_files(temp_dir)

        if not files_to_analyze:
            print("No supported files found to analyze.")
            return

        print(
            f"\nFound {len(files_to_analyze)} files to analyze. Starting AI analysis with Gemini...")

        markdown_report = f"# AI Analysis Report for `{repo_url}` (Generated by Google Gemini)\n\n"
        markdown_report += "This report provides a high-level analysis of the key files in the repository, generated by an AI agent using Google's Gemini model.\n\n"

        for i, file_path in enumerate(files_to_analyze):
            relative_path = os.path.relpath(file_path, temp_dir)
            print(f"[{i+1}/{len(files_to_analyze)}] Analyzing: {relative_path}...")

            # Note: We no longer pass a 'client' object around.
            summary = get_code_summary(client, file_path, temp_dir)

            markdown_report += f"## Analysis of `{relative_path}`\n\n"
            markdown_report += f"{summary}\n\n"
            markdown_report += "---\n\n"

        generate_report(repo_url, markdown_report)


if __name__ == "__main__":
    main()
