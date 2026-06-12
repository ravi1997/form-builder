#!/usr/bin/env python3
"""
Agent Communication Protocol - Shared File-based System
Enables agents to communicate, consult, and collaborate using shared files
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum

class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    CONSULTATION = "consultation"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AgentMessage:
    """Structured message for agent communication"""
    id: str
    type: MessageType
    from_agent: str
    to_agent: Optional[str]
    subject: str
    content: str
    priority: Priority
    timestamp: str
    context: Dict[str, Any]
    requires_response: bool
    response_to: Optional[str]
    ttl: int  # Time to live in seconds

@dataclass
class ConsultationRequest:
    """Request for agent consultation/consultation"""
    id: str
    from_agent: str
    to_agents: List[str]
    question: str
    context: Dict[str, Any]
    expertise_required: List[str]
    deadline: str
    responses: List[Dict]

class AgentCommunicationProtocol:
    """Protocol for agent-to-agent communication using shared files"""
    
    def __init__(self, communication_dir: str = None):
        self.comm_dir = Path(communication_dir) if communication_dir else Path.home() / ".kilo" / "communication"
        self.comm_dir.mkdir(parents=True, exist_ok=True)
        
        self.inbox_dir = self.comm_dir / "inbox"
        self.outbox_dir = self.comm_dir / "outbox"
        self.consultations_dir = self.comm_dir / "consultations"
        self.broadcasts_dir = self.comm_dir / "broadcasts"
        
        for dir_path in [self.inbox_dir, self.outbox_dir, self.consultations_dir, self.broadcasts_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self.message_ttl = 3600  # 1 hour default
        self.cleanup_interval = 300  # 5 minutes
        
        # Start cleanup thread
        import threading
        def cleanup():
            while True:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired_messages()
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
    
    def send_message(self, from_agent: str, to_agent: str, subject: str, 
                   content: str, priority: Priority = Priority.MEDIUM,
                   context: Dict = None, requires_response: bool = False,
                   response_to: str = None) -> str:
        """Send a direct message to another agent"""
        message_id = str(uuid.uuid4())
        
        message = AgentMessage(
            id=message_id,
            type=MessageType.REQUEST,
            from_agent=from_agent,
            to_agent=to_agent,
            subject=subject,
            content=content,
            priority=priority,
            timestamp=datetime.now().isoformat(),
            context=context or {},
            requires_response=requires_response,
            response_to=response_to,
            ttl=self.message_ttl
        )
        
        # Save to outbox
        outbox_file = self.outbox_dir / f"{from_agent}_{message_id}.json"
        with open(outbox_file, 'w') as f:
            json.dump(asdict(message), f, indent=2, default=str)
        
        # Save to recipient's inbox
        inbox_file = self.inbox_dir / f"{to_agent}_{message_id}.json"
        with open(inbox_file, 'w') as f:
            json.dump(asdict(message), f, indent=2, default=str)
        
        return message_id
    
    def send_broadcast(self, from_agent: str, subject: str, content: str,
                      priority: Priority = Priority.MEDIUM, context: Dict = None):
        """Send broadcast message to all agents"""
        message_id = str(uuid.uuid4())
        
        message = AgentMessage(
            id=message_id,
            type=MessageType.BROADCAST,
            from_agent=from_agent,
            to_agent=None,
            subject=subject,
            content=content,
            priority=priority,
            timestamp=datetime.now().isoformat(),
            context=context or {},
            requires_response=False,
            response_to=None,
            ttl=self.message_ttl
        )
        
        # Save to broadcasts directory
        broadcast_file = self.broadcasts_dir / f"{message_id}.json"
        with open(broadcast_file, 'w') as f:
            json.dump(asdict(message), f, indent=2, default=str)
        
        return message_id
    
    def request_consultation(self, from_agent: str, to_agents: List[str], 
                           question: str, context: Dict = None,
                           expertise_required: List[str] = None,
                           deadline_seconds: int = 300) -> str:
        """Request consultation from other agents"""
        consultation_id = str(uuid.uuid4())
        
        consultation = ConsultationRequest(
            id=consultation_id,
            from_agent=from_agent,
            to_agents=to_agents,
            question=question,
            context=context or {},
            expertise_required=expertise_required or [],
            deadline=(datetime.now().timestamp() + deadline_seconds),
            responses=[]
        )
        
        # Save consultation request
        consultation_file = self.consultations_dir / f"{consultation_id}.json"
        with open(consultation_file, 'w') as f:
            json.dump(asdict(consultation), f, indent=2, default=str)
        
        # Send notification to target agents
        for to_agent in to_agents:
            self.send_message(
                from_agent=from_agent,
                to_agent=to_agent,
                subject=f"Consultation Request: {question[:50]}...",
                content=f"Please provide consultation on: {question}",
                priority=Priority.HIGH,
                context={
                    "consultation_id": consultation_id,
                    "deadline": consultation.deadline,
                    "expertise_required": expertise_required
                },
                requires_response=True
            )
        
        return consultation_id
    
    def respond_to_consultation(self, consultation_id: str, from_agent: str, 
                               response: str, confidence: float = 1.0):
        """Respond to a consultation request"""
        consultation_file = self.consultations_dir / f"{consultation_id}.json"
        
        if not consultation_file.exists():
            return False
        
        with open(consultation_file, 'r') as f:
            consultation_data = json.load(f)
        
        # Add response
        response_obj = {
            "agent": from_agent,
            "response": response,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        consultation_data["responses"].append(response_obj)
        
        with open(consultation_file, 'w') as f:
            json.dump(consultation_data, f, indent=2, default=str)
        
        return True
    
    def get_inbox_messages(self, agent_id: str) -> List[AgentMessage]:
        """Get all messages in agent's inbox"""
        messages = []
        
        for message_file in self.inbox_dir.glob(f"{agent_id}_*.json"):
            try:
                with open(message_file, 'r') as f:
                    message_data = json.load(f)
                    message = AgentMessage(**message_data)
                    messages.append(message)
            except Exception as e:
                print(f"Error reading message file {message_file}: {e}")
        
        return sorted(messages, key=lambda x: x.timestamp, reverse=True)
    
    def get_consultation_requests(self, agent_id: str) -> List[ConsultationRequest]:
        """Get consultation requests for an agent"""
        consultations = []
        
        for consultation_file in self.consultations_dir.glob("*.json"):
            try:
                with open(consultation_file, 'r') as f:
                    consultation_data = json.load(f)
                    consultation = ConsultationRequest(**consultation_data)
                    
                    # Check if agent is in the target list
                    if agent_id in consultation.to_agents:
                        consultations.append(consultation)
            except Exception as e:
                print(f"Error reading consultation file {consultation_file}: {e}")
        
        return consultations
    
    def get_broadcast_messages(self, since_timestamp: str = None) -> List[AgentMessage]:
        """Get broadcast messages since a timestamp"""
        messages = []
        
        for broadcast_file in self.broadcasts_dir.glob("*.json"):
            try:
                with open(broadcast_file, 'r') as f:
                    message_data = json.load(f)
                    message = AgentMessage(**message_data)
                    
                    if since_timestamp is None or message.timestamp >= since_timestamp:
                        messages.append(message)
            except Exception as e:
                print(f"Error reading broadcast file {broadcast_file}: {e}")
        
        return sorted(messages, key=lambda x: x.timestamp, reverse=True)
    
    def mark_message_read(self, agent_id: str, message_id: str):
        """Mark a message as read (remove from inbox)"""
        message_file = self.inbox_dir / f"{agent_id}_{message_id}.json"
        if message_file.exists():
            message_file.unlink()
    
    def _cleanup_expired_messages(self):
        """Clean up expired messages"""
        current_time = datetime.now().timestamp()
        
        # Clean up inbox messages
        for message_file in self.inbox_dir.glob("*.json"):
            try:
                with open(message_file, 'r') as f:
                    message_data = json.load(f)
                    message = AgentMessage(**message_data)
                    
                    # Check TTL
                    message_time = datetime.fromisoformat(message.timestamp).timestamp()
                    if current_time - message_time > message.ttl:
                        message_file.unlink()
            except:
                # Remove corrupted files
                message_file.unlink()
        
        # Clean up outbox messages
        for message_file in self.outbox_dir.glob("*.json"):
            try:
                with open(message_file, 'r') as f:
                    message_data = json.load(f)
                    message = AgentMessage(**message_data)
                    
                    message_time = datetime.fromisoformat(message.timestamp).timestamp()
                    if current_time - message_time > message.ttl:
                        message_file.unlink()
            except:
                message_file.unlink()
        
        # Clean up expired consultations
        for consultation_file in self.consultations_dir.glob("*.json"):
            try:
                with open(consultation_file, 'r') as f:
                    consultation_data = json.load(f)
                    consultation = ConsultationRequest(**consultation_data)
                    
                    if current_time > consultation.deadline:
                        consultation_file.unlink()
            except:
                consultation_file.unlink()

class AgentCommunicationClient:
    """Client for agents to use the communication protocol"""
    
    def __init__(self, agent_id: str, protocol: AgentCommunicationProtocol):
        self.agent_id = agent_id
        self.protocol = protocol
    
    def send_message(self, to_agent: str, subject: str, content: str, **kwargs):
        """Send a message to another agent"""
        return self.protocol.send_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            subject=subject,
            content=content,
            **kwargs
        )
    
    def send_broadcast(self, subject: str, content: str, **kwargs):
        """Send a broadcast message"""
        return self.protocol.send_broadcast(
            from_agent=self.agent_id,
            subject=subject,
            content=content,
            **kwargs
        )
    
    def request_consultation(self, to_agents: List[str], question: str, **kwargs):
        """Request consultation from other agents"""
        return self.protocol.request_consultation(
            from_agent=self.agent_id,
            to_agents=to_agents,
            question=question,
            **kwargs
        )
    
    def get_messages(self):
        """Get all messages for this agent"""
        return self.protocol.get_inbox_messages(self.agent_id)
    
    def get_consultations(self):
        """Get consultation requests for this agent"""
        return self.protocol.get_consultation_requests(self.agent_id)
    
    def get_broadcasts(self, since_timestamp: str = None):
        """Get broadcast messages"""
        return self.protocol.get_broadcast_messages(since_timestamp)
    
    def respond_to_consultation(self, consultation_id: str, response: str, **kwargs):
        """Respond to a consultation request"""
        return self.protocol.respond_to_consultation(
            consultation_id=consultation_id,
            from_agent=self.agent_id,
            response=response,
            **kwargs
        )
    
    def mark_message_read(self, message_id: str):
        """Mark a message as read"""
        return self.protocol.mark_message_read(self.agent_id, message_id)

if __name__ == "__main__":
    # Example usage
    protocol = AgentCommunicationProtocol("/home/ravi/workspace/form-builder/.kilo/communication")
    
    # Create communication clients for different agents
    agent1_client = AgentCommunicationClient("agent-1", protocol)
    agent2_client = AgentCommunicationClient("agent-2", protocol)
    agent3_client = AgentCommunicationClient("agent-3", protocol)
    
    # Send messages
    msg_id = agent1_client.send_message(
        to_agent="agent-2",
        subject="Code Review Request",
        content="Please review the backend API implementation",
        priority=Priority.HIGH
    )
    
    # Request consultation
    consultation_id = agent1_client.request_consultation(
        to_agents=["agent-2", "agent-3"],
        question="What's the best approach for handling authentication?",
        expertise_required=["security", "backend"],
        deadline_seconds=600
    )
    
    # Check messages
    messages = agent2_client.get_messages()
    print(f"Agent 2 has {len(messages)} messages")
    
    consultations = agent2_client.get_consultations()
    print(f"Agent 2 has {len(consultations)} consultation requests")
    
    print("Communication protocol initialized successfully")