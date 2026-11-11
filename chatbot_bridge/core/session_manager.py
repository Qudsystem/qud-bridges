"""Session management for browser profiles and chatbot sessions."""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import shutil


@dataclass
class Session:
    """
    Represents an active chatbot session.
    
    Attributes:
        id: Unique session identifier
        chatbot_name: Name of chatbot platform (deepseek, chatgpt, claude)
        profile_path: Path to browser profile directory
        created_at: Session creation timestamp
        last_activity: Last activity timestamp
        is_active: Whether session is currently active
        conversation_history: List of conversation messages
        executed_commands: List of executed command IDs
        metadata: Additional session metadata
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chatbot_name: str = ""
    profile_path: str = ""
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_active: bool = True
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    executed_commands: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "chatbot_name": self.chatbot_name,
            "profile_path": self.profile_path,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "is_active": self.is_active,
            "conversation_history": self.conversation_history,
            "executed_commands": self.executed_commands,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            chatbot_name=data.get("chatbot_name", ""),
            profile_path=data.get("profile_path", ""),
            created_at=data.get("created_at", time.time()),
            last_activity=data.get("last_activity", time.time()),
            is_active=data.get("is_active", True),
            conversation_history=data.get("conversation_history", []),
            executed_commands=data.get("executed_commands", []),
            metadata=data.get("metadata", {})
        )
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.update_activity()
    
    def add_executed_command(self, command_id: str) -> None:
        """
        Add executed command ID to history.
        
        Args:
            command_id: Unique command identifier
        """
        self.executed_commands.append(command_id)
        self.update_activity()
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """
        Get recent conversation messages.
        
        Args:
            count: Number of recent messages to return
            
        Returns:
            List of recent messages
        """
        return self.conversation_history[-count:] if self.conversation_history else []
    
    def is_expired(self, max_idle_hours: int = 24) -> bool:
        """
        Check if session is expired based on inactivity.
        
        Args:
            max_idle_hours: Maximum idle time in hours
            
        Returns:
            True if session is expired
        """
        idle_time = time.time() - self.last_activity
        return idle_time > (max_idle_hours * 3600)


class SessionManager:
    """
    Manages browser sessions and profiles for multiple chatbots.
    
    Features:
    - Session creation and persistence
    - Browser profile management
    - Session cleanup and expiration
    - Multi-chatbot support
    """
    
    def __init__(self, sessions_dir: str = "./sessions"):
        """
        Initialize session manager.
        
        Args:
            sessions_dir: Directory to store browser profiles and session data
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Active sessions in memory
        self.active_sessions: Dict[str, Session] = {}
        
        # Load existing sessions
        self._load_sessions()
    
    def create_session(
        self,
        chatbot_name: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new browser session profile.
        
        Args:
            chatbot_name: Name of chatbot (deepseek, chatgpt, claude)
            session_id: Optional custom session ID
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Create profile directory
        profile_path = self.sessions_dir / chatbot_name / session_id
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Create session object
        session = Session(
            id=session_id,
            chatbot_name=chatbot_name,
            profile_path=str(profile_path),
            metadata=metadata or {}
        )
        
        # Store in memory and persist
        self.active_sessions[session_id] = session
        self._save_session(session)
        
        return session_id
    
    def load_session(self, session_id: str) -> Optional[Session]:
        """
        Load existing session.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Session object if exists, None otherwise
        """
        # Check if already in memory
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Try to load from disk
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                session = Session.from_dict(data)
                
                # Verify profile path exists
                if Path(session.profile_path).exists():
                    self.active_sessions[session_id] = session
                    return session
                else:
                    # Profile missing, remove session
                    session_file.unlink(missing_ok=True)
                    
            except (json.JSONDecodeError, KeyError):
                # Corrupted session file, remove it
                session_file.unlink(missing_ok=True)
        
        return None
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID (load if not in memory).
        
        Args:
            session_id: Session ID
            
        Returns:
            Session object if exists, None otherwise
        """
        return self.load_session(session_id)
    
    def list_sessions(
        self,
        chatbot_name: Optional[str] = None,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all available sessions.
        
        Args:
            chatbot_name: Filter by chatbot name (all if None)
            active_only: Only return active sessions
            
        Returns:
            List of session metadata dictionaries
        """
        sessions = []
        
        # Check all session files
        for chatbot_dir in self.sessions_dir.iterdir():
            if not chatbot_dir.is_dir():
                continue
            
            if chatbot_name and chatbot_dir.name != chatbot_name:
                continue
            
            for session_dir in chatbot_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                
                session_id = session_dir.name
                session = self.load_session(session_id)
                
                if session:
                    if active_only and not session.is_active:
                        continue
                    
                    sessions.append({
                        "id": session.id,
                        "chatbot_name": session.chatbot_name,
                        "created_at": session.created_at,
                        "last_activity": session.last_activity,
                        "is_active": session.is_active,
                        "message_count": len(session.conversation_history),
                        "command_count": len(session.executed_commands)
                    })
        
        # Sort by last activity (most recent first)
        sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session and its profile.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        try:
            # Remove from memory
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Remove profile directory
            profile_path = Path(session.profile_path)
            if profile_path.exists():
                shutil.rmtree(profile_path)
            
            # Remove session file
            session_file = self._get_session_file_path(session_id)
            session_file.unlink(missing_ok=True)
            
            return True
            
        except Exception:
            return False
    
    def cleanup_expired_sessions(self, max_idle_hours: int = 24) -> int:
        """
        Clean up expired sessions.
        
        Args:
            max_idle_hours: Maximum idle time before expiration
            
        Returns:
            Number of sessions cleaned up
        """
        cleaned_count = 0
        
        for session_info in self.list_sessions():
            session_id = session_info["id"]
            session = self.get_session(session_id)
            
            if session and session.is_expired(max_idle_hours):
                if self.delete_session(session_id):
                    cleaned_count += 1
        
        return cleaned_count
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Update session activity timestamp.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if updated successfully
        """
        session = self.get_session(session_id)
        if session:
            session.update_activity()
            self._save_session(session)
            return True
        return False
    
    def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        Add message to session conversation history.
        
        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            
        Returns:
            True if added successfully
        """
        session = self.get_session(session_id)
        if session:
            session.add_message(role, content)
            self._save_session(session)
            return True
        return False
    
    def add_executed_command(self, session_id: str, command_id: str) -> bool:
        """
        Add executed command to session history.
        
        Args:
            session_id: Session ID
            command_id: Command ID
            
        Returns:
            True if added successfully
        """
        session = self.get_session(session_id)
        if session:
            session.add_executed_command(command_id)
            self._save_session(session)
            return True
        return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about all sessions."""
        sessions = self.list_sessions()
        
        stats = {
            "total_sessions": len(sessions),
            "active_sessions": len([s for s in sessions if s["is_active"]]),
            "chatbots": {},
            "total_messages": sum(s["message_count"] for s in sessions),
            "total_commands": sum(s["command_count"] for s in sessions)
        }
        
        # Per-chatbot stats
        for session in sessions:
            chatbot = session["chatbot_name"]
            if chatbot not in stats["chatbots"]:
                stats["chatbots"][chatbot] = {
                    "sessions": 0,
                    "active": 0,
                    "messages": 0,
                    "commands": 0
                }
            
            stats["chatbots"][chatbot]["sessions"] += 1
            if session["is_active"]:
                stats["chatbots"][chatbot]["active"] += 1
            stats["chatbots"][chatbot]["messages"] += session["message_count"]
            stats["chatbots"][chatbot]["commands"] += session["command_count"]
        
        return stats
    
    def _load_sessions(self) -> None:
        """Load all sessions from disk into memory."""
        if not self.sessions_dir.exists():
            return
        
        for chatbot_dir in self.sessions_dir.iterdir():
            if not chatbot_dir.is_dir():
                continue
            
            for session_dir in chatbot_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                
                session_id = session_dir.name
                self.load_session(session_id)
    
    def _save_session(self, session: Session) -> None:
        """Save session to disk."""
        session_file = self._get_session_file_path(session.id)
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def _get_session_file_path(self, session_id: str) -> Path:
        """Get path to session metadata file."""
        # Find session by ID across all chatbot directories
        for chatbot_dir in self.sessions_dir.iterdir():
            if not chatbot_dir.is_dir():
                continue
            
            session_dir = chatbot_dir / session_id
            if session_dir.exists():
                return session_dir / "session.json"
        
        # If not found, assume it's in a generic location
        return self.sessions_dir / "unknown" / session_id / "session.json"