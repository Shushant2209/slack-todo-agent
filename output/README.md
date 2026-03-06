# 🔔 Slack Todo Agent

An OpenHands-powered agent that runs daily at 6 PM, scans all your Slack channels for @mentions, and creates an interactive todo list in your Slack DM with buttons to mark tasks as done.

![Flow Diagram](./plan/flow_diagram.html)

## ✨ Features

- **Daily Automatic Scan**: Runs every evening at 6 PM
- **All Channels**: Scans all Slack channels where you're a member
- **Interactive Todo List**: Each task has a "View Original" button and "Mark Done" button
- **Slack DM Delivery**: Results are sent directly to your Slack DM
- **Secure**: Your token is stored in environment variables, never logged

## 📋 Requirements

- Python 3.8+
- Slack Bot Token

## 🚀 Setup Instructions

### Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click "Create New App"
2. Choose "From scratch"
3. Name your app (e.g., "Todo Agent") and select your workspace
4. Click "Create App"

### Step 2: Add OAuth Scopes

Scroll down to "OAuth Tokens for Your Workspace" and click "Request to Install" or manually add scopes:

1. Go to **OAuth & Permissions** in the left sidebar
2. Add these **Bot Token Scopes**:
   - `channels:read` - List all channels
   - `groups:read` - List private channels  
   - `im:read` - Read DMs
   - `im:write` - Send DMs to user
   - `chat:write` - Send messages to channels
   - `users:read` - Look up user info
   - `conversations:read` - Read channel history

### Step 3: Install App to Workspace

1. Click "Install App" (or "Request to Install" if shown)
2. Review the permissions and click "Allow"
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Run the Agent

```bash
# Navigate to output directory
cd output

# Install dependencies
pip install -r requirements.txt

# Set your token (replace with your actual token)
export SLACK_BOT_TOKEN=xoxb-your-token-here

# Run the agent
python slack_todo_agent.py
```

The agent will:
1. Run immediately to test the setup
2. Schedule to run daily at 6 PM
3. Send you a DM with all your mentioned tasks

## ☁️ Running on GitHub Actions (Free!)

The agent can run on GitHub's servers - no local machine needed!

### Step 1: Push to GitHub

1. Create a new repository on GitHub
2. Push the code:
   ```bash
   git init
   git add .
   git commit -m "Add Slack Todo Agent"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/slack-todo-agent.git
   git push -u origin main
   ```

### Step 2: Add Slack Token as Secret

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `SLACK_BOT_TOKEN`
4. Value: Your Slack bot token (starts with `xoxb-`)
5. Click "Add secret"

### Step 3: That's It! 🎉

The workflow runs automatically:
- **Daily at 6 PM** (UTC time)
- You can also manually trigger it from the Actions tab
- Check the Actions tab to see run history

### Manual Run

Go to your repo → Actions → "Slack Todo Agent" → "Run workflow"

## 🔒 Security

- **Token Storage**: Uses environment variable `SLACK_BOT_TOKEN`
- **No Hardcoding**: Token is never stored in code
- **Minimal Permissions**: Only requests scopes needed for functionality
- **Secure API**: All Slack communications use HTTPS

## 📁 Files

```
output/
├── slack_todo_agent.py    # Main agent
├── requirements.txt       # Python dependencies  
└── README.md             # This file
```

## 🎯 How It Works

1. **6 PM Daily**: Scheduler triggers the agent
2. **Authenticate**: Connects to Slack using your bot token
3. **Scan Channels**: Finds all channels where you're a member
4. **Find Mentions**: Searches for messages where you're @mentioned
5. **Create Todo**: Builds an interactive message with buttons
6. **Send DM**: Posts the todo list to your Slack DM

## ❓ Troubleshooting

### "Failed to authenticate"
- Verify your token is correct and starts with `xoxb-`
- Make sure the app is installed to your workspace

### "Could not access channel"
- The bot needs to be a member of private channels
- Reinstall the app and invite the bot to those channels

### "No mentions found"
- Make sure you're @mentioned (not just in a thread)
- Check that you're a member of the channels

## 🤖 Built With

- [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)
- [Slack SDK for Python](https://github.com/slackapi/python-slack-sdk)
- [APScheduler](https://apscheduler.readthedocs.io/)
