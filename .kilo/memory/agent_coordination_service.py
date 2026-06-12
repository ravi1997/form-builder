#!/usr/bin/env python3
"""
Agent Coordination Service - Shared Memory System
Provides coordination, communication, and task distribution for multiple agents
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading
import logging

class AgentCoordinationService:
    """Central coordination service for multi-agent collaboration"""
    
    def __init__(self, memory_dir: str = None):
        self.memory_dir = Path(memory_dir) if memory_dir else Path.home() / ".kilo" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.agents_file = self.memory_dir / "agents.json"
        self.tasks_file = self.memory_dir / "tasks.json"
        self.context_file = self.memory_dir / "shared_context.json"
        self.channels_file = self.memory_dir / "channels.json"
        
        self.lock = threading.Lock()
        self.system_config = {
            "max_concurrent_agents": 10,
            "task_timeout": 3600,  # 1 hour
            "heartbeat_interval": 30,  # 30 seconds
            "cleanup_interval": 300,  # 5 minutes
            "enable_consultation": True,
            "enable_task_distribution": True
        }
        
        self._initialize_files()
        self._start_cleanup_thread()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _initialize_files(self):
        """Initialize memory files if they don't exist"""
        for file_path in [self.agents_file, self.tasks_file, self.context_file, self.channels_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump({}, f, indent=2)
    
    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file with error handling"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: Path, data: Dict):
        """Save JSON file with error handling"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error saving {file_path}: {e}")
    
    def register_agent(self, agent_id: str, name: str, agent_type: str, 
                      provider: str, capabilities: List[str] = None) -> bool:
        """Register a new agent in the coordination system"""
        with self.lock:
            agents = self._load_json(self.agents_file)
            
            agents[agent_id] = {
                "id": agent_id,
                "name": name,
                "type": agent_type,
                "provider": provider,
                "capabilities": capabilities or [],
                "status": "active",
                "last_seen": datetime.now().isoformat(),
                "current_task": None,
                "shared_memory_access": True
            }
            
            self._save_json(self.agents_file, agents)
            self.logger.info(f"Registered agent: {name} ({agent_id})")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the coordination system"""
        with self.lock:
            agents = self._load_json(self.agents_file)
            if agent_id in agents:
                del agents[agent_id]
                self._save_json(self.agents_file, agents)
                self.logger.info(f"Unregistered agent: {agent_id}")
                return True
            return False
    
    def update_agent_status(self, agent_id: str, status: str, current_task: str = None):
        """Update agent status and heartbeat"""
        with self.lock:
            agents = self._load_json(self.agents_file)
            if agent_id in agents:
                agents[agent_id]["status"] = status
                agents[agent_id]["last_seen"] = datetime.now().isoformat()
                if current_task:
                    agents[agent_id]["current_task"] = current_task
                self._save_json(self.agents_file, agents)
    
    def create_task(self, title: str, description: str, priority: str = "medium",
                   created_by: str = None, dependencies: List[str] = None,
                   collaboration_mode: str = "sequential") -> str:
        """Create a new task for agent coordination"""
        task_id = str(uuid.uuid4())
        
        with self.lock:
            tasks = self._load_json(self.tasks_file)
            
            tasks[task_id] = {
                "id": task_id,
                "title": title,
                "description": description,
                "status": "pending",
                "priority": priority,
                "assigned_to": [],
                "created_by": created_by or "system",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed_at": None,
                "dependencies": dependencies or [],
                "context": {},
                "results": {},
                "collaboration_mode": collaboration_mode
            }
            
            self._save_json(self.tasks_file, tasks)
            self.logger.info(f"Created task: {title} ({task_id})")
            return task_id
    
    def assign_task(self, task_id: str, agent_ids: List[str]) -> bool:
        """Assign task to one or more agents"""
        with self.lock:
            tasks = self._load_json(self.tasks_file)
            if task_id not in tasks:
                return False
            
            tasks[task_id]["assigned_to"] = agent_ids
            tasks[task_id]["status"] = "assigned"
            tasks[task_id]["updated_at"] = datetime.now().isoformat()
            
            self._save_json(self.tasks_file, tasks)
            
            # Update agent status
            agents = self._load_json(self.agents_file)
            for agent_id in agent_ids:
                if agent_id in agents:
                    agents[agent_id]["current_task"] = task_id
                    agents[agent_id]["status"] = "busy"
            self._save_json(self.agents_file, agents)
            
            return True
    
    def update_task_status(self, task_id: str, status: str, results: Dict = None) -> bool:
        """Update task status and results"""
        with self.lock:
            tasks = self._load_json(self.tasks_file)
            if task_id not in tasks:
                return False
            
            tasks[task_id]["status"] = status
            tasks[task_id]["updated_at"] = datetime.now().isoformat()
            
            if status == "completed":
                tasks[task_id]["completed_at"] = datetime.now().isoformat()
            
            if results:
                tasks[task_id]["results"].update(results)
            
            self._save_json(self.tasks_file, tasks)
            
            # Update agent status if task is completed
            if status == "completed":
                agents = self._load_json(self.agents_file)
                for agent_id in tasks[task_id]["assigned_to"]:
                    if agent_id in agents:
                        agents[agent_id]["current_task"] = None
                        agents[agent_id]["status"] = "idle"
                self._save_json(self.agents_file, agents)
            
            return True
    
    def get_active_agents(self) -> List[Dict]:
        """Get list of active agents"""
        agents = self._load_json(self.agents_file)
        active_agents = []
        
        for agent_id, agent_data in agents.items():
            if agent_data["status"] in ["active", "busy"]:
                # Check if agent is still alive (heartbeat within 2x interval)
                last_seen = datetime.fromisoformat(agent_data["last_seen"])
                if (datetime.now() - last_seen).seconds < self.system_config["heartbeat_interval"] * 2:
                    active_agents.append(agent_data)
                else:
                    # Mark as offline
                    agent_data["status"] = "offline"
        
        return active_agents
    
    def get_pending_tasks(self) -> List[Dict]:
        """Get list of pending tasks"""
        tasks = self._load_json(self.tasks_file)
        pending_tasks = []
        
        for task_id, task_data in tasks.items():
            if task_data["status"] in ["pending", "assigned"]:
                pending_tasks.append(task_data)
        
        return sorted(pending_tasks, key=lambda x: x["priority"])
    
    def create_communication_channel(self, channel_id: str, name: str, 
                                   channel_type: str = "broadcast") -> bool:
        """Create a communication channel between agents"""
        with self.lock:
            channels = self._load_json(self.channels_file)
            
            channels[channel_id] = {
                "name": name,
                "type": channel_type,
                "participants": [],
                "messages": []
            }
            
            self._save_json(self.channels_file, channels)
            return True
    
    def send_message(self, channel_id: str, from_agent: str, message: str, 
                   to_agent: str = None) -> bool:
        """Send message to a communication channel"""
        with self.lock:
            channels = self._load_json(self.channels_file)
            if channel_id not in channels:
                return False
            
            message_obj = {
                "id": str(uuid.uuid4()),
                "from": from_agent,
                "to": to_agent,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            channels[channel_id]["messages"].append(message_obj)
            self._save_json(self.channels_file, channels)
            return True
    
    def get_messages(self, channel_id: str, agent_id: str = None) -> List[Dict]:
        """Get messages from a communication channel"""
        channels = self._load_json(self.channels_file)
        if channel_id not in channels:
            return []
        
        messages = channels[channel_id]["messages"]
        
        # Filter messages for specific agent if provided
        if agent_id:
            messages = [msg for msg in messages 
                       if msg["to"] is None or msg["to"] == agent_id or msg["from"] == agent_id]
        
        return messages
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup():
            while True:
                time.sleep(self.system_config["cleanup_interval"])
                self._cleanup_expired_tasks()
                self._cleanup_offline_agents()
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
    
    def _cleanup_expired_tasks(self):
        """Clean up expired tasks"""
        tasks = self._load_json(self.tasks_file)
        current_time = datetime.now()
        
        for task_id, task_data in list(tasks.items()):
            if task_data["status"] in ["in_progress", "assigned"]:
                created_time = datetime.fromisoformat(task_data["created_at"])
                if (current_time - created_time).seconds > self.system_config["task_timeout"]:
                    task_data["status"] = "failed"
                    task_data["updated_at"] = current_time.isoformat()
        
        self._save_json(self.tasks_file, tasks)
    
    def _cleanup_offline_agents(self):
        """Clean up offline agents"""
        agents = self._load_json(self.agents_file)
        current_time = datetime.now()
        
        for agent_id, agent_data in list(agents.items()):
            last_seen = datetime.fromisoformat(agent_data["last_seen"])
            if (current_time - last_seen).seconds > self.system_config["heartbeat_interval"] * 3:
                agent_data["status"] = "offline"
        
        self._save_json(self.agents_file, agents)

if __name__ == "__main__":
    # Example usage
    coordinator = AgentCoordinationService("/home/ravi/workspace/form-builder/.kilo/memory")
    
    # Register agents
    coordinator.register_agent("agent-1", "Code Reviewer", "primary", "kilo", 
                             ["code_review", "analysis"])
    coordinator.register_agent("agent-2", "Frontend Specialist", "primary", "kilo", 
                             ["frontend", "ui"])
    coordinator.register_agent("agent-3", "Backend Specialist", "external", "codex", 
                             ["backend", "api"])
    
    print("Agent coordination service initialized")
    print(f"Active agents: {len(coordinator.get_active_agents())}")
    print(f"Pending tasks: {len(coordinator.get_pending_tasks())}")