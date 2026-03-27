"""
Calendar Manager Agent - Content Scheduling and Queue Management
Part of the Scheduler Robot multi-agent system (Agent 1/4)

Responsibilities:
- Analyze publishing history and identify patterns
- Manage content queue and prioritization
- Calculate optimal publishing times
- Detect and resolve scheduling conflicts
- Generate visual calendar views
"""
from typing import List, Optional, Dict, Any
from crewai import Agent
from dotenv import load_dotenv
import os

from agents.scheduler.tools.calendar_tools import (
    CalendarAnalyzer,
    QueueManager,
    TimeOptimizer
)

load_dotenv()


class CalendarManagerAgent:
    """
    Calendar Manager Agent for content scheduling and queue management.
    First agent in the Scheduler Robot pipeline.
    Analyzes patterns and determines optimal publishing times.
    """

    def __init__(self, llm_model: str = "groq/mixtral-8x7b-32768"):
        """
        Initialize Calendar Manager with scheduling tools.

        Args:
            llm_model: LiteLLM model string (default: groq/mixtral-8x7b-32768)
        """
        self.llm_model = llm_model

        # Initialize tools
        self.calendar_analyzer = CalendarAnalyzer()
        self.queue_manager = QueueManager()
        self.time_optimizer = TimeOptimizer()

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create the CrewAI Calendar Manager Agent"""
        return Agent(
            role="Content Calendar Manager",
            goal=(
                "Optimize content publishing schedules by analyzing historical patterns, "
                "managing the content queue efficiently, and determining optimal publishing times "
                "that maximize audience engagement while maintaining consistent content cadence."
            ),
            backstory=(
                "You are an expert content calendar manager with deep understanding of "
                "audience behavior patterns, publishing strategies, and editorial planning. "
                "You analyze historical publishing data to identify trends, manage content backlogs, "
                "and ensure optimal timing for maximum reach and engagement. You excel at "
                "detecting conflicts, balancing priorities, and creating efficient publishing schedules "
                "that align with both audience preferences and content goals."
            ),
            tools=[
                self.calendar_analyzer.analyze_publishing_history,
                self.calendar_analyzer.get_publishing_statistics,
                self.queue_manager.add_to_queue,
                self.queue_manager.get_queue_status,
                self.queue_manager.detect_scheduling_conflicts,
                self.time_optimizer.calculate_optimal_time,
                self.time_optimizer.generate_calendar_view
            ],
            llm=self.llm_model,  # CrewAI uses LiteLLM internally
            verbose=True,
            allow_delegation=False
        )

    def schedule_content(
        self,
        content_data: Dict[str, Any],
        auto_schedule: bool = True
    ) -> Dict[str, Any]:
        """
        Schedule a content item for publishing.

        Args:
            content_data: Content information (title, path, type, priority, etc.)
            auto_schedule: Whether to automatically calculate optimal time

        Returns:
            Scheduling result with queue position and recommended time
        """
        try:
            # Add to queue
            queue_result = self.queue_manager.add_to_queue(content_data)

            if not queue_result.get('success'):
                return queue_result

            # Calculate optimal time if auto_schedule
            if auto_schedule:
                optimal_time = self.time_optimizer.calculate_optimal_time(
                    content_type=content_data.get('content_type', 'article'),
                    priority=content_data.get('priority', 3)
                )

                return {
                    **queue_result,
                    "optimal_time": optimal_time
                }

            return queue_result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_calendar(self, days: int = 14) -> Dict[str, Any]:
        """
        Get visual calendar view.

        Args:
            days: Number of days to show

        Returns:
            Calendar view with scheduled content
        """
        return self.time_optimizer.generate_calendar_view(days=days)

    def analyze_performance(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze publishing performance.

        Args:
            days: Number of days to analyze

        Returns:
            Performance analysis with patterns and recommendations
        """
        return self.calendar_analyzer.analyze_publishing_history(days=days)

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return self.queue_manager.get_queue_status()

    def detect_conflicts(self) -> Dict[str, Any]:
        """Detect scheduling conflicts"""
        return self.queue_manager.detect_scheduling_conflicts()


# Create default instance
def create_calendar_manager(llm_model: str = "mixtral-8x7b-32768") -> CalendarManagerAgent:
    """Factory function to create Calendar Manager Agent"""
    return CalendarManagerAgent(llm_model=llm_model)
