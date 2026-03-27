"""
Image Robot - Multi-Agent Image Generation and CDN Management System
Orchestrates 4 specialized agents for automated image generation, optimization,
and CDN deployment for blog articles.

Agents:
1. Image Strategist - Analyzes content and defines visual strategy
2. Image Generator - Generates images via Robolly API
3. Image Optimizer - Compresses and creates responsive variants
4. CDN Manager - Uploads to Bunny.net and manages CDN delivery
"""

from agents.images.image_crew import ImageRobotCrew, create_image_robot_crew

__all__ = [
    "ImageRobotCrew",
    "create_image_robot_crew"
]
