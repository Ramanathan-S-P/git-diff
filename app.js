const express = require('express');
const axios = require('axios');
const dotenv = require('dotenv');

// Load environment variables from .env file if available
dotenv.config();

const app = express();
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_API_URL = "https://api.github.com";

// Middleware to parse JSON requests
app.use(express.json());

// Route to get commit details
app.get('/repositories/:owner/:repository/commits/:oid', async (req, res) => {
    const { owner, repository, oid } = req.params;

    try {
        // Set headers for GitHub API requests
        const headers = {};
        if (GITHUB_TOKEN) {
            headers['Authorization'] = `token ${GITHUB_TOKEN}`;
        }

        // Get commit details from GitHub API
        const commitUrl = `${GITHUB_API_URL}/repos/${owner}/${repository}/commits/${oid}`;
        const commitResponse = await axios.get(commitUrl, { headers });

        if (commitResponse.status !== 200) {
            return res.status(commitResponse.status).json({ error: 'Error fetching commit data' });
        }

        const commitData = commitResponse.data;

        // Format response
        const formattedCommit = {
            oid: commitData.sha,
            message: commitData.commit.message,
            author: {
                name: commitData.commit.author.name,
                date: commitData.commit.author.date,
                email: commitData.commit.author.email
            },
            committer: {
                name: commitData.commit.committer.name,
                date: commitData.commit.committer.date,
                email: commitData.commit.committer.email
            },
            parents: commitData.parents.map(parent => ({ oid: parent.sha }))
        };

        res.status(200).json(formattedCommit);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Route to get commit diff
app.get('/repositories/:owner/:repository/commits/:oid/diff', async (req, res) => {
    const { owner, repository, oid } = req.params;

    try {
        const headers = {};
        if (GITHUB_TOKEN) {
            headers['Authorization'] = `token ${GITHUB_TOKEN}`;
        }

        // Get commit details
        const commitUrl = `${GITHUB_API_URL}/repos/${owner}/${repository}/commits/${oid}`;
        const commitResponse = await axios.get(commitUrl, { headers });

        if (commitResponse.status !== 200) {
            return res.status(commitResponse.status).json({ error: 'Error fetching commit data' });
        }

        const commitData = commitResponse.data;

        // Get parent commit SHA
        const parents = commitData.parents;
        if (!parents || parents.length === 0) {
            return res.status(404).json({ error: 'No parent commit found' });
        }

        const parentCommitSha = parents[0].sha;

        // Get diff between parent and current commit
        const diffUrl = `${GITHUB_API_URL}/repos/${owner}/${repository}/compare/${parentCommitSha}...${oid}`;
        const diffResponse = await axios.get(diffUrl, { headers });

        if (diffResponse.status !== 200) {
            return res.status(diffResponse.status).json({ error: 'Error fetching diff' });
        }

        const diffData = diffResponse.data;

        // Format the diff output
        const formattedDiff = diffData.files.map(file => {
            const hunks = [];
            if (file.patch) {
                const lines = file.patch.split('\n');
                let hunkHeader = '';
                let baseLineStart = null;
                let headLineStart = null;
                let hunkLines = [];

                lines.forEach(line => {
                    if (line.startsWith('@@')) {
                        // Parse the hunk header
                        if (hunkLines.length > 0) {
                            hunks.push({ header: hunkHeader, lines: hunkLines });
                        }
                        hunkHeader = line;
                        [baseLineStart, headLineStart] = parseHunkHeader(line);
                        hunkLines = [];
                    } else {
                        const { baseLineNumber, headLineNumber, content } = parseLineInfo(line, baseLineStart, headLineStart);
                        hunkLines.push({
                            baseLineNumber,
                            headLineNumber,
                            content
                        });
                        if (baseLineNumber !== null) baseLineStart++;
                        if (headLineNumber !== null) headLineStart++;
                    }
                });

                if (hunkLines.length > 0) {
                    hunks.push({ header: hunkHeader, lines: hunkLines });
                }
            }

            return {
                changeKind: file.status.toUpperCase(),  // MODIFIED, ADDED, DELETED
                headFile: { path: file.filename },
                baseFile: { path: file.previous_filename || file.filename },
                hunks
            };
        });

        res.status(200).json(formattedDiff);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Parse the hunk header for base and head starting lines
function parseHunkHeader(header) {
    const match = header.match(/@@ -(\d+),\d+ \+(\d+),\d+ @@/);
    if (match) {
        const baseStart = parseInt(match[1]);
        const headStart = parseInt(match[2]);
        return [baseStart, headStart];
    }
    return [null, null];
}

// Parse a line from the diff and determine its base and head line numbers
function parseLineInfo(line, baseLineStart, headLineStart) {
    let baseLineNumber = null;
    let headLineNumber = null;
    let content = line;

    if (line.startsWith('+')) {
        headLineNumber = headLineStart;
        content = line.substring(1); // Remove the '+'
    } else if (line.startsWith('-')) {
        baseLineNumber = baseLineStart;
        content = line.substring(1); // Remove the '-'
    } else {
        baseLineNumber = baseLineStart;
        headLineNumber = headLineStart;
    }

    return { baseLineNumber, headLineNumber, content };
}

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
