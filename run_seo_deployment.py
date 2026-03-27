#!/usr/bin/env python3
"""
SEO Agent Orchestration Script
Runs SEO agents and deploys content to GitHub
Can be run manually or via cron job
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.seo.research_analyst import ResearchAnalyst
from agents.seo.content_strategist import ContentStrategistAgent
from agents.seo.tools.github_tools import GitHubContentDeployer, check_deployment_status
from agents.seo.tools.repo_analyzer import GitHubRepoAnalyzer


def run_seo_pipeline(
    topic: str,
    auto_deploy: bool = True,
    dry_run: bool = False,
    target_repo: Optional[str] = None
) -> dict:
    """
    Run complete SEO pipeline: Analyze Repo → Research → Strategy → Deploy
    
    Args:
        topic: Target topic/keyword
        auto_deploy: Auto commit and push to GitHub
        dry_run: Test without committing
        target_repo: GitHub repo URL to analyze (optional)
        
    Returns:
        Pipeline execution results
    """
    print(f"\n{'='*60}")
    print(f"🤖 SEO PIPELINE - {topic}")
    print(f"{'='*60}\n")
    
    results = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "steps": {},
        "success": False
    }
    
    try:
        # Step 0: Analyze target repo (if provided)
        repo_analysis = None
        if target_repo:
            print("🔍 Step 0: Analyzing Target Repository...")
            print("-" * 60)
            
            analyzer = GitHubRepoAnalyzer()
            repo_analysis = analyzer.generate_analysis_report(
                repo_url=target_repo,
                target_topics=[topic]
            )
            
            results["steps"]["repo_analysis"] = {
                "success": True,
                "framework": repo_analysis["structure"]["framework"],
                "total_pages": repo_analysis["seo_data"]["total_pages"],
                "internal_links": repo_analysis["internal_links"]["total_links"]
            }
            print(f"✅ Analyzed {repo_analysis['seo_data']['total_pages']} pages\n")
        
        # Step 1: Research Analysis
        print("📊 Step 1/3: Research Analysis...")
        print("-" * 60)
        
        analyst = ResearchAnalyst()
        research_output = analyst.run_analysis(
            topic=topic,
            competitors=[]  # Auto-detect from SERP
        )
        
        results["steps"]["research"] = {
            "success": True,
            "output_length": len(research_output)
        }
        print(f"✅ Research complete ({len(research_output)} chars)\n")
        
        # Step 2: Content Strategy
        print("📝 Step 2/3: Content Strategy...")
        print("-" * 60)
        
        strategist = ContentStrategistAgent()
        
        # Add repo context to research if available
        context_insights = research_output
        if repo_analysis:
            context_insights += f"\n\n## TARGET SITE ANALYSIS\n"
            context_insights += f"Framework: {repo_analysis['structure']['framework']}\n"
            context_insights += f"Existing pages: {repo_analysis['seo_data']['total_pages']}\n"
            if repo_analysis['content_gaps']:
                context_insights += f"Content gaps identified: {len(repo_analysis['content_gaps']['missing_topics'])}\n"
        
        strategy_output = strategist.run_strategy(
            research_insights=context_insights,
            target_keyword=topic,
            content_count=5
        )
        
        results["steps"]["strategy"] = {
            "success": True,
            "output_length": len(str(strategy_output))
        }
        print(f"✅ Strategy complete ({len(str(strategy_output))} chars)\n")
        
        # Step 3: Deploy to GitHub
        if not dry_run:
            print("🚀 Step 3/3: GitHub Deployment...")
            print("-" * 60)
            
            deployer = GitHubContentDeployer()
            
            # Create strategy document
            deploy_result = deployer.deploy_seo_content(
                content=str(strategy_output),
                title=f"Content Strategy: {topic}",
                metadata={
                    "description": f"Comprehensive content strategy for {topic}",
                    "keywords": [topic, "seo", "content strategy"],
                    "author": "SEO Bot"
                },
                subdirectory="strategies",
                auto_commit=auto_deploy
            )
            
            results["steps"]["deployment"] = deploy_result
            
            if deploy_result["success"]:
                print(f"✅ Deployed to: {deploy_result['filepath']}")
                if deploy_result.get("git_commit"):
                    print(f"   Commit: {deploy_result['git_commit'].get('commit_hash', 'N/A')[:7]}")
            else:
                print(f"⚠️ Deployment saved locally (no commit)")
        else:
            print("🧪 Step 3/3: Dry Run - Skipping deployment")
            results["steps"]["deployment"] = {"dry_run": True}
        
        results["success"] = True
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {str(e)}")
        results["error"] = str(e)
        results["success"] = False
    
    print(f"\n{'='*60}")
    print(f"Pipeline {'✅ COMPLETE' if results['success'] else '❌ FAILED'}")
    print(f"{'='*60}\n")
    
    return results


def run_batch_topics(
    topics: List[str],
    auto_deploy: bool = True,
    delay_seconds: int = 60
):
    """
    Run SEO pipeline for multiple topics with delay.
    
    Args:
        topics: List of topics to process
        auto_deploy: Auto commit and push
        delay_seconds: Delay between topics
    """
    import time
    
    print(f"\n🔄 BATCH MODE: {len(topics)} topics\n")
    
    results = []
    for i, topic in enumerate(topics, 1):
        print(f"\n[Topic {i}/{len(topics)}]")
        result = run_seo_pipeline(topic, auto_deploy=auto_deploy)
        results.append(result)
        
        # Delay between topics (except last one)
        if i < len(topics):
            print(f"\n⏳ Waiting {delay_seconds}s before next topic...")
            time.sleep(delay_seconds)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 BATCH SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results if r["success"])
    print(f"Total: {len(results)} | Success: {successful} | Failed: {len(results) - successful}")
    print(f"{'='*60}\n")


def show_status():
    """Show current deployment status."""
    print("\n📊 DEPLOYMENT STATUS\n")
    status = check_deployment_status()
    
    print(f"Git Branch: {status['git']['branch']}")
    print(f"Repository Clean: {'✅' if status['git']['is_clean'] else '⚠️ Changes pending'}")
    
    if status['git']['modified_files']:
        print(f"\nModified files: {len(status['git']['modified_files'])}")
        for f in status['git']['modified_files'][:5]:
            print(f"  - {f}")
    
    if status['git']['untracked_files']:
        print(f"\nUntracked files: {len(status['git']['untracked_files'])}")
        for f in status['git']['untracked_files'][:5]:
            print(f"  - {f}")
    
    print(f"\nWebsite pages: {status['website_pages_count']}")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SEO Agent Orchestration - Research, Strategy, Deploy"
    )
    
    parser.add_argument(
        "topic",
        nargs="?",
        help="Target topic/keyword to analyze"
    )
    
    parser.add_argument(
        "--batch",
        nargs="+",
        help="Process multiple topics (space-separated)"
    )
    
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Skip GitHub deployment"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without committing"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show deployment status"
    )
    
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Delay between batch topics (seconds, default: 60)"
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help="Target GitHub repository URL to analyze (fetches latest before analysis)"
    )
    
    args = parser.parse_args()
    
    # Show status
    if args.status:
        show_status()
        return
    
    # Batch mode
    if args.batch:
        run_batch_topics(
            topics=args.batch,
            auto_deploy=not args.no_deploy,
            delay_seconds=args.delay
        )
        return
    
    # Single topic
    if args.topic:
        run_seo_pipeline(
            topic=args.topic,
            auto_deploy=not args.no_deploy,
            dry_run=args.dry_run,
            target_repo=args.repo
        )
        return
    
    # No arguments - show help
    parser.print_help()
    print("\n💡 Examples:")
    print("  python run_seo_deployment.py 'content marketing'")
    print("  python run_seo_deployment.py 'seo' --repo https://github.com/user/site.git")
    print("  python run_seo_deployment.py --batch 'seo tools' 'link building' --repo https://github.com/user/site.git")
    print("  python run_seo_deployment.py --status")
    print("  python run_seo_deployment.py 'seo strategy' --dry-run")
    print()


if __name__ == "__main__":
    main()
