"""
Personal Context Management System
Stores and retrieves user-specific information like schedules, assignments, preferences
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

CONTEXT_DIR = "user_contexts"
GLOBAL_CONTEXT_FILE = "global_user_context.json"

class PersonalContextManager:
    """Manages personal context for users"""
    
    def __init__(self):
        """Initialize context manager and ensure storage directory exists"""
        # Use absolute path relative to this file's location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.context_dir = os.path.join(base_dir, CONTEXT_DIR)
        
        if not os.path.exists(self.context_dir):
            os.makedirs(self.context_dir)
            print(f"📁 Created context directory: {self.context_dir}")
    
    def _get_context_file(self, session_id: str = None) -> str:
        """Get the file path for context (now global, session_id ignored)"""
        return os.path.join(self.context_dir, GLOBAL_CONTEXT_FILE)
    
    def get_context(self, session_id: str = None) -> Dict:
        """
        Retrieve personal context for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Dict with personal context data
        """
        context_file = self._get_context_file(session_id)
        
        if os.path.exists(context_file):
            with open(context_file, 'r') as f:
                return json.load(f)
        
        # Return default empty context
        return {
            "schedule": [],
            "assignments": [],
            "preferences": {},
            "notes": [],
            "created_at": datetime.now().isoformat()
        }
    
    def save_context(self, session_id: str = None, context: Dict = None) -> bool:
        """
        Save personal context (global, session_id ignored)
        
        Args:
            session_id: Ignored (kept for backwards compatibility)
            context: Context data to save
            
        Returns:
            bool: Success status
        """
        try:
            if context is None:
                print("Error saving context: context is None")
                return False
                
            context_file = self._get_context_file()
            context["updated_at"] = datetime.now().isoformat()
            
            with open(context_file, 'w') as f:
                json.dump(context, f, indent=2)
            
            print(f"✅ Successfully saved context to {context_file}")
            return True
        except Exception as e:
            import traceback
            print(f"❌ Error saving context: {e}")
            print(traceback.format_exc())
            return False
    
    def add_schedule_item(self, session_id: str = None, course: str = "", day: str = "", 
                         time: str = "", location: str = "") -> bool:
        """Add a class to the schedule (global context)"""
        context = self.get_context()
        
        schedule_item = {
            "course": course,
            "day": day,
            "time": time,
            "location": location,
            "added_at": datetime.now().isoformat()
        }
        
        context["schedule"].append(schedule_item)
        return self.save_context(context=context)
    
    def add_assignment(self, session_id: str = None, title: str = "", due_date: str = "", 
                      course: str = "", description: str = "") -> bool:
        """Add an assignment/deadline (global context)"""
        context = self.get_context()
        
        assignment = {
            "title": title,
            "due_date": due_date,
            "course": course,
            "description": description,
            "completed": False,
            "added_at": datetime.now().isoformat()
        }
        
        context["assignments"].append(assignment)
        return self.save_context(context=context)
    
    def add_note(self, session_id: str = None, note: str = "", category: str = "general") -> bool:
        """Add a personal note (global context)"""
        context = self.get_context()
        
        note_item = {
            "content": note,
            "category": category,
            "added_at": datetime.now().isoformat()
        }
        
        context["notes"].append(note_item)
        return self.save_context(context=context)
    
    def set_preference(self, session_id: str = None, key: str = "", value: str = "") -> bool:
        """Set a user preference (global context)"""
        context = self.get_context()
        context["preferences"][key] = value
        return self.save_context(context=context)
    
    def format_context_for_llm(self, session_id: str = None) -> str:
        """
        Format personal context as a string for LLM consumption (global context)
        
        Returns:
            Formatted string with all personal context
        """
        context = self.get_context()
        
        parts = []
        
        # Schedule
        if context["schedule"]:
            parts.append("STUDENT SCHEDULE:")
            for item in context["schedule"]:
                parts.append(f"  - {item['course']} on {item['day']} at {item['time']}")
                if item.get('location'):
                    parts[-1] += f" (Location: {item['location']})"
        
        # Assignments
        if context["assignments"]:
            parts.append("\nASSIGNMENTS & DEADLINES:")
            for item in context["assignments"]:
                status = "✓ Completed" if item.get('completed') else "⏳ Pending"
                parts.append(f"  - {item['title']} - Due: {item['due_date']} [{status}]")
                if item.get('course'):
                    parts[-1] += f" (Course: {item['course']})"
        
        # Preferences
        if context["preferences"]:
            parts.append("\nUSER PREFERENCES:")
            for key, value in context["preferences"].items():
                parts.append(f"  - {key}: {value}")
        
        # Notes
        if context["notes"]:
            parts.append("\nPERSONAL NOTES:")
            for item in context["notes"]:
                parts.append(f"  - [{item['category']}] {item['content']}")
        
        if not parts:
            return ""
        
        return "\n".join(parts)
    
    def delete_item(self, context_type: str, index: int) -> bool:
        """
        Delete a specific item from context
        
        Args:
            context_type: Type of context ('schedule', 'assignment', 'note')
            index: Index of item to delete
            
        Returns:
            bool: Success status
        """
        context = self.get_context()
        
        try:
            if context_type == "schedule" and 0 <= index < len(context["schedule"]):
                context["schedule"].pop(index)
            elif context_type == "assignment" and 0 <= index < len(context["assignments"]):
                context["assignments"].pop(index)
            elif context_type == "note" and 0 <= index < len(context["notes"]):
                context["notes"].pop(index)
            elif context_type == "preference":
                # For preferences, index is actually the key
                pass  # Handle separately
            else:
                return False
            
            return self.save_context(context=context)
        except Exception as e:
            print(f"Error deleting item: {e}")
            return False
    
    def delete_preference(self, key: str) -> bool:
        """Delete a specific preference by key"""
        context = self.get_context()
        
        try:
            if key in context["preferences"]:
                del context["preferences"][key]
                return self.save_context(context=context)
            return False
        except Exception as e:
            print(f"Error deleting preference: {e}")
            return False
    
    def clear_context(self, session_id: str = None) -> bool:
        """Clear all personal context (global)"""
        context_file = self._get_context_file()
        try:
            if os.path.exists(context_file):
                os.remove(context_file)
            return True
        except Exception as e:
            print(f"Error clearing context: {e}")
            return False
