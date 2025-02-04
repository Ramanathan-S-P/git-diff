from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

# GitHub API URL template
GITHUB_DIFF_URL = "https://api.github.com/repos/{owner}/{repo}/commits/{commit}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/repositories/<owner>/<repo>/commits/<oid>/diff', methods=['GET'])
def get_diff(owner, repo, oid):
    try:
        # Make a request to GitHub API to get the commit diff
        url = GITHUB_DIFF_URL.format(owner=owner, repo=repo, commit=oid)
        
        # Send the request (replace 'your_token' with your GitHub token if needed for private repos)
        headers = {"Accept": "application/vnd.github.v3.diff"}  # GitHub-specific header for diff
        response = requests.get(url, headers=headers)

        # Check if the response is successful
        if response.status_code == 200:
            diff = response.text  # Get the diff text from the response
            return jsonify({"diff": diff})
        else:
            return jsonify({"error": f"Failed to fetch diff: {response.status_code}, {response.text}"}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
