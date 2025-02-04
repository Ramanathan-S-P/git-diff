import re
from flask import Flask, jsonify, request
import requests
import os
import json
app = Flask(__name__)

# Optional GitHub token for authenticated requests (helps avoid rate limits)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# GitHub API base URL
GITHUB_API_URL = "https://api.github.com"
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

GITHUB_API_URL = "https://api.github.com"
@app.route("/repositories/<owner>/<repository>/commits/<oid>", methods=["GET"])
def get_commit_details(owner, repository, oid):
    try:
        headers = {}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        # Get the commit data for the specified commit SHA
        commit_url = f"{GITHUB_API_URL}/repos/{owner}/{repository}/commits/{oid}"
        commit_response = requests.get(commit_url, headers=headers)

        if commit_response.status_code != 200:
            return jsonify({"error": "Error fetching commit data"}), commit_response.status_code

        commit_data = commit_response.json()

        # Format the response to match the desired structure
        formatted_commit = {
            "oid": commit_data.get("sha"),
            "message": commit_data.get("commit", {}).get("message"),
            "author": {
                "name": commit_data.get("commit", {}).get("author", {}).get("name"),
                "date": commit_data.get("commit", {}).get("author", {}).get("date"),
                "email": commit_data.get("commit", {}).get("author", {}).get("email")
            },
            "committer": {
                "name": commit_data.get("commit", {}).get("committer", {}).get("name"),
                "date": commit_data.get("commit", {}).get("committer", {}).get("date"),
                "email": commit_data.get("commit", {}).get("committer", {}).get("email")
            },
            "parents": [
                {
                    "oid": parent.get("sha")
                } for parent in commit_data.get("parents", [])
            ]
        }

        return app.response_class(
            response=json.dumps(formatted_commit, indent=4, sort_keys=False),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route("/repositories/<owner>/<repository>/commits/<oid>/diff", methods=["GET"])
def get_commit_diff(owner, repository, oid):
    try:
        # Prepare headers for the GitHub API request
        headers = {}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        # Get the commit details from GitHub API
        commit_url = f"{GITHUB_API_URL}/repos/{owner}/{repository}/commits/{oid}"
        commit_response = requests.get(commit_url, headers=headers)

        if commit_response.status_code != 200:
            return jsonify({"error": f"Error fetching commit: {commit_response.json()}"}), commit_response.status_code

        commit_data = commit_response.json()

        # Get the parent commit (first parent)
        parents = commit_data.get('parents')
        if not parents:
            return jsonify({"error": "No parent commit found"}), 404

        parent_commit_sha = parents[0]['sha']

        # Get the diff between the current commit and the parent commit
        diff_url = f"{GITHUB_API_URL}/repos/{owner}/{repository}/compare/{parent_commit_sha}...{oid}"
        diff_response = requests.get(diff_url, headers=headers)

        if diff_response.status_code != 200:
            return jsonify({"error": f"Error fetching diff: {diff_response.json()}"}), diff_response.status_code

        diff_data = diff_response.json()

        # Process the diff output to match the desired format
        formatted_diff = []
        for file in diff_data.get('files', []):
            if 'patch' not in file:
                continue

            hunks = []
            lines = file['patch'].splitlines()
            header = ""
            hunk_lines = []
            base_line_start = None
            head_line_start = None

            for line in lines:
                if line.startswith('@@'):
                    # Parse the hunk header to get the base and head line starting points
                    if hunk_lines:
                        hunks.append({"header": header, "lines": hunk_lines})
                    header = line
                    base_line_start, head_line_start = parse_hunk_header(line)
                    hunk_lines = []
                else:
                    base_line_number, head_line_number, content = parse_line_info(line, base_line_start, head_line_start)
                    hunk_lines.append({
                        "baseLineNumber": base_line_number,
                        "headLineNumber": head_line_number,
                        "content": content
                    })
                    # Increment line numbers accordingly
                    if base_line_number is not None:
                        base_line_start += 1
                    if head_line_number is not None:
                        head_line_start += 1
            if hunk_lines:
                hunks.append({"header": header, "lines": hunk_lines})

            formatted_diff.append({
                "changeKind": file.get('status').upper(),  # MODIFIED, ADDED, DELETED, etc.
                "headFile": {
                    "path": file.get('filename')
                },
                "baseFile": {
                    "path": file.get('previous_filename', file.get('filename'))
                },
                "hunks": hunks
            })

        return app.response_class(
            response=json.dumps(formatted_diff, indent=4, sort_keys=False),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def parse_hunk_header(header):
    """
    Parses the hunk header to extract the starting line numbers for both the base and head versions of the file.
    The header is in the format: @@ -start_base,num_lines_base +start_head,num_lines_head @@
    """
    match = re.match(r'@@ -(\d+),\d+ \+(\d+),\d+ @@', header)
    if match:
        base_start = int(match.group(1))
        head_start = int(match.group(2))
        return base_start, head_start
    return None, None


def parse_line_info(line, base_line_start, head_line_start):
    """
    Parses a line from the diff and returns the base line number, head line number, and content.
    It assumes that '+' indicates an added line and '-' indicates a removed line.
    """
    base_line_number = None
    head_line_number = None
    content = line

    if line.startswith('+'):
        head_line_number = head_line_start
        content = line[1:]  # Remove the '+' symbol
    elif line.startswith('-'):
        base_line_number = base_line_start
        content = line[1:]  # Remove the '-' symbol
    else:
        base_line_number = base_line_start
        head_line_number = head_line_start
        content = line

    return base_line_number, head_line_number, content


if __name__ == "__main__":
    app.run(debug=True)
