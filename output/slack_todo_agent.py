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
    
    def __init__(self, token: str, user_id: str = None):
        self.client = WebClient(token=token)
        self.user_id = user_id  # The user whose mentions to scan
        self.todos = []
        
    def get_my_user_id(self) -> str:
        """Get the authenticated user's ID (the bot itself)."""
        try:
            response = self.client.auth_test()
            bot_user_id = response['user_id']
            logger.info(f"Authenticated as bot: {response['user']} ({bot_user_id})")
            return bot_user_id
        except SlackApiError as e:
            logger.error(f"Failed to authenticate: {e}")
            raise
    
    def get_user_id_by_email(self, email: str) -> str:
        """Get a user's ID by their email address."""
        try:
            response = self.client.users_lookupByEmail(email=email)
            if response['ok']:
                user_id = response['user']['id']
                logger.info(f"Found user: {response['user']['name']} ({user_id}) for email: {email}")
                return user_id
            else:
                logger.error(f"User not found for email: {email}")
                return None
        except SlackApiError as e:
            logger.error(f"Failed to look up user by email: {e}")
            return None
    
    def get_user_id_by_name(self, username: str) -> str:
        """Get a user's ID by their username (without @)."""
        try:
            # Try direct ID first
            if username.startswith('U'):
                return username
            
            # List users and find by name
            response = self.client.users_list()
            if response['ok']:
                for user in response['members']:
                    if user.get('name') == username:
                        logger.info(f"Found user: {user['name']} ({user['id']})")
                        return user['id']
            logger.error(f"User not found: {username}")
            return None
        except SlackApiError as e:
            logger.error(f"Failed to look up user by name: {e}")
            return None
            
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
            # Open DM with the TARGET USER (not the bot)
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
        # If user_id not set, we can't scan
        if not self.user_id:
            logger.error("No user_id set! Please specify a user to scan mentions for.")
            return
            
        logger.info("=" * 50)
        logger.info("Starting Slack Todo Agent scan...")
        logger.info(f"Scanning for mentions of user: {self.user_id}")
        logger.info("=" * 50)
        
        # Scan for mentions
        mentions = self.scan_all_channels()
        
        # Send todo list
        self.send_todo_list(mentions)
        
        logger.info("=" * 50)
        logger.info("Agent scan complete!")
        logger.info("=" * 50)


def main(run_once: bool = False):
    """Main entry point with optional scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Slack Todo Agent')
    parser.add_argument('--run-once', action='store_true', 
                       help='Run once and exit (for GitHub Actions)')
    parser.add_argument('--user', type=str, 
                       help='Your Slack username (without @) or email to scan mentions for')
    args = parser.parse_args()
    
    # Get token from environment
    token = os.environ.get('SLACK_BOT_TOKEN')
    target_user = args.user or os.environ.get('SLACK_USER')
    
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
   - users:read.email
3. Install the app to your workspace
4. Copy your Bot User OAuth Token (starts with xoxb-)
5. Set as GitHub Secret: SLACK_BOT_TOKEN=xoxb-your-token
6. Set your username: SLACK_USER=your-username
        """)
        return
    
    if not target_user:
        logger.error("No user specified! Set SLACK_USER env var or use --user argument")
        logger.info("\nUsage: python slack_todo_agent.py --user YOUR_SLACK_USERNAME")
        return
    
    # Create agent
    agent = SlackTodoAgent(token, user_id=None)
    
    # Test connection first
    try:
        bot_id = agent.get_my_user_id()
    except Exception as e:
        logger.error(f"Failed to connect to Slack: {e}")
        return
    
    # Look up the target user (the person whose mentions to scan)
    logger.info(f"Looking up user: {target_user}")
    if '@' in target_user:
        user_id = agent.get_user_id_by_email(target_user)
    else:
        user_id = agent.get_user_id_by_name(target_user)
    
    if not user_id:
        logger.error(f"Could not find user: {target_user}")
        return
    
    # Set the user ID to scan for
    agent.user_id = user_id
    
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
