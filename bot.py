import discord
import asyncio
import os
import logging
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

@dataclass
class VotingSession:
    """Encapsulates data for a voting session"""
    target_message: discord.Message
    votes: Set[int] = field(default_factory=set)
    vote_count: int = 0
    
    def add_vote(self, user_id: int) -> bool:
        """Add a vote if user hasn't voted. Returns True if vote was added."""
        if user_id not in self.votes:
            self.votes.add(user_id)
            self.vote_count += 1
            return True
        return False
    
    def remove_vote(self, user_id: int) -> bool:
        """Remove a vote if user has voted. Returns True if vote was removed."""
        if user_id in self.votes:
            self.votes.remove(user_id)
            self.vote_count -= 1
            return True
        return False

class PinBot(discord.Client):
    def __init__(self, confirm_cap: int, *args, **kwargs):
        # Use minimal intents for better performance
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(intents=intents, *args, **kwargs)
        
        self.confirm_cap = confirm_cap
        self.voting_sessions: Dict[int, VotingSession] = {}
        self.emoji_cache: Dict[int, str] = {}
        self.session_lock = asyncio.Lock()
        
        # Precompute number emojis for performance
        self.number_emojis = [
            "<:pixel1:942438227380408350>", "<:pixel2:942438227258785802>", 
            "<:pixel3:942438227585957968>", "<:pixel4:942438227107786804>",
            "<:pixel5:942438227623702589>", "<:pixel6:942438227330089060>",
            "<:pixel7:942438227476901958>", "<:pixel8:942438227002949652>",
            "<:pixel9:942438227405602906>", "<:pixel10:942438227825029160>"
        ]
        
        # Rate limiting
        self.pin_cooldown = defaultdict(float)
        self.PIN_COOLDOWN_SECONDS = 5.0
    
    async def setup_hook(self):
        """Setup method called when bot starts"""
        logger.info(f"Bot starting with confirm_cap: {self.confirm_cap}")
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self.periodic_cleanup())
    
    async def periodic_cleanup(self):
        """Periodically clean up old voting sessions"""
        while not self.is_closed():
            await asyncio.sleep(300)  # Clean up every 5 minutes
            
            async with self.session_lock:
                current_time = asyncio.get_event_loop().time()
                to_remove = []
                
                for msg_id, session in self.voting_sessions.items():
                    # Remove sessions older than 1 hour
                    if current_time - session.target_message.created_at.timestamp() > 3600:
                        to_remove.append(msg_id)
                
                for msg_id in to_remove:
                    del self.voting_sessions[msg_id]
                    logger.info(f"Cleaned up old voting session: {msg_id}")
    
    def get_number_emoji(self, num: int) -> str:
        """Get number emoji efficiently"""
        if 1 <= num <= 10:
            return self.number_emojis[num - 1]
        return "❓"
    
    async def on_ready(self):
        logger.info(f'Bot logged in as {self.user}')
    
    async def on_message(self, message: discord.Message):
        """Handle new messages"""
        if message.author == self.user or not message.reference:
            return
        
        # Check if bot is mentioned
        if not (message.content.startswith(f"<@{self.user.id}>") or 
                message.content.startswith(f"<@!{self.user.id}>")):
            return
        
        try:
            # Get the referenced message
            target_message = await message.channel.fetch_message(message.reference.message_id)
            
            if self.confirm_cap == 0:
                await self.pin_message_safely(target_message)
                return
            
            # Create voting session
            async with self.session_lock:
                session = VotingSession(target_message=target_message)
                self.voting_sessions[message.id] = session
            
            # Add reactions
            reactions = ["✅", "<:slash:1284496769551568927>", self.get_number_emoji(self.confirm_cap)]
            
            for emoji in reactions:
                try:
                    await message.add_reaction(emoji)
                except discord.HTTPException as e:
                    logger.warning(f"Failed to add reaction {emoji}: {e}")
                    
        except discord.NotFound:
            await message.reply("❌ Referenced message not found!", delete_after=10)
        except discord.HTTPException as e:
            logger.error(f"HTTP error in on_message: {e}")
            await message.reply("❌ An error occurred while processing your request.", delete_after=10)
    
    async def pin_message_safely(self, message: discord.Message):
        """Pin message with rate limiting and error handling"""
        current_time = asyncio.get_event_loop().time()
        channel_id = message.channel.id
        
        # Check rate limit
        if current_time - self.pin_cooldown[channel_id] < self.PIN_COOLDOWN_SECONDS:
            logger.warning(f"Pin rate limited for channel {channel_id}")
            return False
        
        try:
            await message.pin()
            self.pin_cooldown[channel_id] = current_time
            logger.info(f"Successfully pinned message {message.id}")
            return True
        except discord.HTTPException as e:
            logger.error(f"Failed to pin message {message.id}: {e}")
            return False
    
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction additions"""
        if user == self.user or str(reaction.emoji) != "✅":
            return
        
        message_id = reaction.message.id
        
        async with self.session_lock:
            session = self.voting_sessions.get(message_id)
            if not session:
                return
            
            # Add vote
            if session.add_vote(user.id):
                logger.info(f"Vote added by {user.id} for message {message_id}. Count: {session.vote_count}")
                
                # Check if threshold reached
                if session.vote_count >= self.confirm_cap:
                    success = await self.pin_message_safely(session.target_message)
                    if success:
                        # Clean up the session
                        del self.voting_sessions[message_id]
    
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction removals"""
        if user == self.user or str(reaction.emoji) != "✅":
            return
        
        message_id = reaction.message.id
        
        async with self.session_lock:
            session = self.voting_sessions.get(message_id)
            if not session:
                return
            
            # Remove vote
            if session.remove_vote(user.id):
                logger.info(f"Vote removed by {user.id} for message {message_id}. Count: {session.vote_count}")
    
    async def close(self):
        """Clean shutdown"""
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()
        await super().close()

def main():
    """Main entry point"""
    token = os.getenv("TOKEN")
    if not token:
        logger.error("TOKEN environment variable not set!")
        return
    
    try:
        confirm_cap = int(os.getenv("CONFIRM_CAP", "3"))
    except ValueError:
        logger.error("CONFIRM_CAP must be a valid integer!")
        return
    
    if not (0 <= confirm_cap <= 10):
        logger.error("CONFIRM_CAP must be between 0 and 10")
        return
    
    bot = PinBot(confirm_cap=confirm_cap)
    
    try:
        bot.run(token, log_handler=None)  # Use our custom logging
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()