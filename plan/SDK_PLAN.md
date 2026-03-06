# Slack Todo Agent - Technical Implementation Plan

## Overview
An OpenHands Software Agent that runs daily at 6 PM, scans all Slack channels where the user is mentioned, and creates an interactive todo list in the user's Slack DM with buttons to mark tasks as done.

## Requirements Summary
- **Run Time**: Every evening at 6 PM
- **Data Source**: All Slack channels where user is a member
- **Output**: Interactive Slack message with buttons in user's DM
- **Interactive Feature**: Button on each todo to view original message and mark as done
- **Security**: Token stored in environment variable, minimal permissions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Slack Todo Agent                         │
├─────────────────────────────────────────────────────────────┤
│  1. Scheduler (APScheduler) - Runs daily at 6 PM           │
│         │                                                    │
│         ▼                                                    │
│  2. Slack Client                                            │
│     - Authenticate via Bot Token                            │
│     - Fetch user ID from mentions                           │
│         │                                                    │
│         ▼                                                    │
│  3. Channel Scanner                                        │
│     - Get all channels user is member of                    │
│     - Search for messages mentioning user                  │
│         │                                                    │
│         ▼                                                    │
│  4. Todo List Builder                                       │
│     - Extract task text from messages                       │
│     - Link to original message                              │
│         │                                                    │
│         ▼                                                    │
│  5. Slack Message Sender                                    │
│     - Post interactive message to user's DM                │
│     - Include action buttons for each todo                  │
└─────────────────────────────────────────────────────────────┘
```

## Slack API Permissions Required
- `channels:read` - List all channels
- `groups:read` - List private channels
- `im:read` - Read DMs
- `im:write` - Send DMs to user
- `chat:write` - Send messages to channels
- `reactions:write` - Add reactions (optional)
- `users:read` - Look up user info

## Implementation Details

### File Structure
```
output/
├── slack_todo_agent.py    # Main agent entry point
├── requirements.txt       # Dependencies
└── README.md             # Setup instructions
```

### Key Components

1. **Scheduler**: Uses `APScheduler` for daily 6 PM execution
2. **Slack Client**: Uses `slack-sdk` for Slack API interactions
3. **Message Parser**: Extracts user mentions and task content
4. **Interactive Blocks**: Slack Block Kit with action buttons

### Security Measures
- Slack token stored in `SLACK_BOT_TOKEN` env var
- Token validated on startup
- No logging of sensitive data
- HTTPS only for API calls

## Setup Steps
1. Create Slack App at api.slack.com
2. Install app to workspace
3. Add required OAuth scopes
4. Set environment variable: `SLACK_BOT_TOKEN=xoxb-...`
5. Run agent with: `python slack_todo_agent.py`

## Interactive Features
- Each todo shows: Task text + "View Original" button + "Mark Done" button
- Buttons trigger Slack interactions
- Original message link uses Slack's message permalink
