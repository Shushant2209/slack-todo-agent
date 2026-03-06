"""
Slack Todo Agent
Runs daily at 6 PM, scans all channels for @mentions, 
and creates an interactive todo list in your Slack DM.

Usage:
    export SLACK_BOT_TOKEN=xoxb-your-token-here
    python slack_todo_agent.py
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SlackTodoAgent:
    """Agent that scans Slack mentions and creates interactive todo lists."""
    
    def __init__(self, token: str):
        self.client = WebClient(token=token)
        self.user_id = None
        self.todos = []
        
    def get_my_user_id(self) -> str:
        """Get the authenticated user's ID."""
        try:
            response = self.client.auth_test()
            self.user_id = response['user_id']
            logger.info(f"Authenticated as user: {response['user']} ({self.user_id})")
            return self.user_id
        except SlackApiError as e:
            logger.error(f"Failed to authenticate: {e}")
            raise
            
    def get_all_channels(self) -> list:
        """Get all channels where the user is a member."""
        channels = []
        cursor = None
        
        try:
            # Get public channels
            while True:
                if cursor:
                    response = self.client.conversations_list(
                        types='public_channel,private_channel',
                        cursor=cursor,
                        limit=100
                    )
                else:
                    response = self.client.conversations_list(
                        types='public_channel,private_channel',
                        limit=100
                    )
                
                for channel in response['channels']:
                    if channel.get('is_member', False):
                        channels.append(channel)
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                    
            logger.info(f"Found {len(channels)} channels where you are a member")
            return channels
            
        except SlackApiError as e:
            logger.error(f"Failed to get channels: {e}")
            return []
    
    def get_user_mentions_in_channel(self, channel_id: str) -> list:
        """Get all messages where the user is mentioned in a channel."""
        mentions = []
        try:
            # Get conversation history
            result = self.client.conversations_history(
                channel=channel_id,
                limit=200  # Get last 200 messages
            )
            
            for message in result['messages']:
                # Check if user is mentioned (either as @user or in thread)
                text = message.get('text', '')
                user_mention = f'<@{self.user_id}>'
                
                if user_mention in text:
                    # Get more context - the full message with thread
                    permalink_result = self.client.chat_getPermalink(
                        channel=channel_id,
                        message_ts=message['ts']
                    )
                    permalink = permalink_result.get('permalink', '')
                    
                    mentions.append({
                        'text': text,
                        'ts': message['ts'],
                        'channel': channel_id,
                        'permalink': permalink,
                        'user': message.get('user', 'unknown'),
                        'timestamp': datetime.fromtimestamp(float(message['ts']))
                    })
                    logger.info(f"Found mention in {channel_id}: {text[:50]}...")
                    
        except SlackApiError as e:
            logger.warning(f"Could not access channel {channel_id}: {e}")
            
        return mentions
    
    def scan_all_channels(self) -> list:
        """Scan all channels for mentions of the user."""
        all_mentions = []
        
        channels = self.get_all_channels()
        logger.info(f"Scanning {len(channels)} channels for mentions...")
        
        for channel in channels:
            mentions = self.get_user_mentions_in_channel(channel['id'])
            all_mentions.extend(mentions)
            
        # Sort by timestamp (newest first)
        all_mentions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"Found {len(all_mentions)} total mentions")
        return all_mentions
    
    def create_todo_blocks(self, mentions: list) -> list:
        """Create Slack Block Kit blocks for the todo list."""
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 Your Daily Todo List",
                "emoji": True
            }
        })
        
        # Info section
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Found *{len(mentions)}* tasks from your Slack mentions today!"
            }
        })
        
        blocks.append({"type": "divider"})
        
        if not mentions:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No new mentions found today. You're all caught up! 🎉"
                }
            })
        else:
            # Add each todo with buttons
            for i, mention in enumerate(mentions):
                # Clean up the message text - remove user mentions for display
                clean_text = mention['text'].replace(f'<@{self.user_id}>', '').strip()
                
                # Truncate if too long
                if len(clean_text) > 200:
                    clean_text = clean_text[:197] + "..."
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{i+1}.* {clean_text}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Original",
                            "emoji": True
                        },
                        "url": mention['permalink'],
                        "action_id": f"view_original_{i}"
                    }
                })
                
                # Add "Mark Done" button
                blocks.append({
                    "type": "actions",
                    "block_id": f"todo_action_{i}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Mark Done",
                                "emoji": True
                            },
                            "style": "primary",
                            "action_id": f"mark_done_{i}",
                            "value": f"{mention['channel']}|{mention['ts']}"
                        }
                    ]
                })
                
                blocks.append({"type": "divider"})
        
        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })
        
        return blocks
    
    def send_todo_list(self, mentions: list):
        """Send the todo list to the user's DM."""
        try:
            # Open DM with user
            response = self.client.conversations_open(users=[self.user_id])
            dm_channel = response['channel']['id']
            
            # Create blocks
            blocks = self.create_todo_blocks(mentions)
            
            # Send message
            result = self.client.chat_postMessage(
                channel=dm_channel,
                blocks=blocks,
                text=f"You have {len(mentions)} new tasks from Slack mentions"
            )
            
            logger.info(f"Successfully sent todo list to DM: {result['ts']}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to send todo list: {e}")
            return False
    
    def run(self):
        """Main agent execution."""
        logger.info("=" * 50)
        logger.info("Starting Slack Todo Agent scan...")
        logger.info("=" * 50)
        
        # Get user ID
        if not self.user_id:
            self.get_my_user_id()
        
        # Scan for mentions
        mentions = self.scan_all_channels()
        
        # Send todo list
        self.send_todo_list(mentions)
        
        logger.info("=" * 50)
        logger.info("Agent scan complete!")
        logger.info("=" * 50)


def main(run_once: bool = False):
    """Main entry point with optional scheduler."""
    # Get token from environment
    token = os.environ.get('SLACK_BOT_TOKEN')
    
    if not token:
        logger.error("SLACK_BOT_TOKEN environment variable not set!")
        logger.info("\n" + "=" * 50)
        logger.info("SETUP INSTRUCTIONS:")
        logger.info("=" * 50)
        logger.info("""
1. Create a Slack App at https://api.slack.com/apps
2. Add the following OAuth Scopes:
   - channels:read
   - groups:read  
   - im:read
   - im:write
   - chat:write
   - users:read
3. Install the app to your workspace
4. Copy your Bot User OAuth Token (starts with xoxb-)
5. Set the token as a GitHub Secret:
   - Go to your repo Settings > Secrets > New repository secret
   - Name: SLACK_BOT_TOKEN
   - Value: xoxb-your-token-here
   
6. The workflow will run automatically at 6 PM daily!
        """)
        return
    
    # Create agent
    agent = SlackTodoAgent(token)
    
    # Test connection first
    try:
        agent.get_my_user_id()
    except Exception as e:
        logger.error(f"Failed to connect to Slack: {e}")
        return
    
    # If run_once mode (GitHub Actions), just run once and exit
    if run_once:
        agent.run()
        return
    
    # Otherwise, run with scheduler
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Schedule to run daily at 6 PM
    scheduler.add_job(
        agent.run,
        'cron',
        hour=18,
        minute=0,
        id='daily_todo_scan'
    )
    
    logger.info("=" * 50)
    logger.info("Slack Todo Agent Started!")
    logger.info("=" * 50)
    logger.info("The agent will run daily at 6:00 PM")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    # Run once immediately to test
    logger.info("\nRunning initial scan to test...")
    agent.run()
    
    # Start scheduler
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\nAgent stopped.")
        

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Slack Todo Agent')
    parser.add_argument('--run-once', action='store_true', 
                       help='Run once and exit (for GitHub Actions)')
    args = parser.parse_args()
    
    main(run_once=args.run_once)
