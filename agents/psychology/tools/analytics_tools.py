"""Tools for fetching analytics data — Google Analytics, content performance"""

from crewai import tool


@tool("fetch_analytics_data")
def fetch_analytics_data(
    property_id: str,
    date_range: str,
) -> str:
    """Fetch Google Analytics data for a property. Returns key metrics.
    Note: Requires google-analytics-data package and credentials.

    Args:
        property_id: GA4 property ID (e.g., '123456789')
        date_range: Date range like '7d', '30d', '90d'
    """
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        days = {"7d": 7, "30d": 30, "90d": 90}.get(date_range, 30)

        client = BetaAnalyticsDataClient()
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
            ],
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            limit=20,
        )

        response = client.run_report(request)

        rows = []
        for row in response.rows:
            rows.append({
                "page": row.dimension_values[0].value,
                "views": int(row.metric_values[0].value),
                "avgDuration": float(row.metric_values[1].value),
                "bounceRate": float(row.metric_values[2].value),
            })

        import json
        return json.dumps({"property_id": property_id, "period": date_range, "pages": rows}, indent=2)

    except ImportError:
        return '{"error": "google-analytics-data package not installed. Install with: pip install google-analytics-data"}'
    except Exception as e:
        return f'{{"error": "GA fetch failed: {str(e)}"}}'


@tool("correlate_content_performance")
def correlate_content_performance(
    content_data_json: str,
    persona_name: str,
) -> str:
    """Correlate content performance data with a persona to identify what resonates.

    Args:
        content_data_json: JSON array of content performance records (title, views, engagement, tags)
        persona_name: Name of the persona to correlate with
    """
    import json

    try:
        data = json.loads(content_data_json)
    except json.JSONDecodeError:
        return '{"error": "Invalid JSON for content data"}'

    if not data:
        return f"No content performance data available for persona '{persona_name}'."

    sorted_by_views = sorted(data, key=lambda x: x.get("views", 0), reverse=True)
    top_content = sorted_by_views[:5]

    all_tags: dict[str, int] = {}
    for item in top_content:
        for tag in item.get("tags", []):
            all_tags[tag] = all_tags.get(tag, 0) + 1

    top_themes = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:5]

    avg_engagement = sum(item.get("engagement", 0) for item in data) / max(len(data), 1)

    report = [
        f"## Content-Persona Correlation: {persona_name}",
        f"**Total pieces analyzed**: {len(data)}",
        f"**Average engagement**: {avg_engagement:.1f}%",
        f"**Top-performing themes**: {[t[0] for t in top_themes]}",
        "",
        "### Top content:",
    ]

    for item in top_content:
        report.append(f"- **{item.get('title', 'Untitled')}** — {item.get('views', 0)} views, {item.get('engagement', 0)}% engagement")

    return "\n".join(report)
