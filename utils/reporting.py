import os
import json
from datetime import datetime

class ReportGenerator:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.reports_dir = "/root/robots/reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = f"{self.agent_name}_report_{self.timestamp}.md"
        self.filepath = os.path.join(self.reports_dir, self.filename)
        
    def create_report(self, task_results: dict):
        """
        Creates a markdown report with the following structure:
        - Agent name and timestamp
        - Summary of tasks completed
        - Key findings/recommendations
        - Performance metrics
        - Next steps
        
        :param task_results: Dictionary containing task execution results
        """
        report = f"# {self.agent_name} Report - {self.timestamp}\n\n"
        
        # Tasks completed section
        report += "## Tasks Completed\n"
        for task, result in task_results.items():
            report += f"- **{task}**: {result.get('status', 'N/A')}\n"
            if 'details' in result:
                report += f"  - {result['details']}\n"
        
        # Recommendations section
        if 'recommendations' in task_results:
            report += "\n## Recommendations\n"
            for rec in task_results['recommendations']:
                report += f"1. {rec}\n"
        
        # Metrics section
        if 'metrics' in task_results:
            report += "\n## Metrics\n"
            for metric, value in task_results['metrics'].items():
                report += f"- **{metric}**: {value}\n"
        
        # Next actions section
        report += "\n## Next Actions\n"
        for i, action in enumerate(task_results.get('next_actions', []), 1):
            report += f"{i}. [ ] {action}\n"
        
        # Save report
        with open(self.filepath, 'w') as f:
            f.write(report)
        
        return self.filepath

    @staticmethod
    def log_to_file(message: str, log_type: str = "INFO"):
        """Appends a message to a daily log file"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_path = f"/root/robots/logs/{date_str}.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {log_type}: {message}\n"
        
        with open(log_path, "a") as f:
            f.write(log_entry)