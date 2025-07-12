import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from airflow.models import Variable
from db.connection import PostgreSQLConnection


logger = logging.getLogger(__name__)


def send_slack_message(message: Dict[str, Any]) -> None:
    """
    Send a message to Slack webhook.
    
    Args:
        message: Slack message payload dictionary
    """
    # Try to get Slack webhook URL from Airflow Variable first, then environment variable
    try:
        slack_webhook_url = Variable.get("slack_webhook_url")
    except KeyError:
        slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        logger.warning("Slack webhook URL not configured. Skipping notification.")
        return
    
    try:
        response = requests.post(
            slack_webhook_url,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        logger.info("Slack notification sent successfully")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Slack notification: {e}")


def send_slack_notification(context: Dict[str, Any]) -> None:
    """
    Send Slack notification for DAG completion or failure.
    
    Args:
        context: Airflow context dictionary containing task instance and DAG run information
    """
    # Try to get Slack webhook URL from Airflow Variable first, then environment variable
    try:
        slack_webhook_url = Variable.get("slack_webhook_url")
    except KeyError:
        slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        logger.warning("Slack webhook URL not configured. Skipping notification.")
        return
    
    # Extract relevant information from context
    dag_id = context.get("dag", {}).dag_id
    task_id = context.get("task_instance", {}).task_id
    execution_date = context.get("execution_date", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    dag_run = context.get("dag_run", {})
    
    # Determine status and color
    if context.get("exception"):
        status = "Failed"
        color = "#FF0000"  # Red
        emoji = ":x:"
    else:
        status = "Success"
        color = "#36a64f"  # Green
        emoji = ":white_check_mark:"
    
    # Build Slack message
    message = {
        "attachments": [
            {
                "color": color,
                "pretext": f"{emoji} DAG Execution {status}",
                "title": f"DAG: {dag_id}",
                "fields": [
                    {
                        "title": "Task",
                        "value": task_id,
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": status,
                        "short": True
                    },
                    {
                        "title": "Execution Date",
                        "value": execution_date,
                        "short": True
                    },
                    {
                        "title": "DAG Run ID",
                        "value": dag_run.run_id if dag_run else "N/A",
                        "short": True
                    }
                ],
                "footer": "Airflow Notification",
                "ts": int(datetime.now().timestamp())
            }
        ]
    }
    
    # Add error details if failed
    if context.get("exception"):
        error_msg = str(context.get("exception", "Unknown error"))
        message["attachments"][0]["fields"].append({
            "title": "Error Message",
            "value": f"```{error_msg[:500]}```",  # Limit error message length
            "short": False
        })
    
    # Send to Slack
    try:
        response = requests.post(
            slack_webhook_url,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Slack notification sent successfully for {dag_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Slack notification: {e}")


def get_recent_anken_info() -> List[Dict[str, Any]]:
    """
    Get recent anken (procurement cases) information from database.
    
    Returns:
        List of dictionaries containing anken information
    """
    db_conn = PostgreSQLConnection()
    anken_list = []
    
    # Get dashboard URL from environment variable or use default
    dashboard_url = os.environ.get('DASHBOARD_URL', 'http://localhost:3032')
    
    try:
        with db_conn.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get only cases that were crawled today, including UUID
                cursor.execute("""
                    SELECT 
                        id,  -- UUID for dashboard link
                        case_id,
                        case_name,
                        org_name,
                        bidding_date,
                        is_eligible_to_bid,
                        eligibility_reason,
                        case_url
                    FROM bidding_cases
                    WHERE DATE(created_at) = CURRENT_DATE
                    ORDER BY created_at DESC
                """)
                
                rows = cursor.fetchall()
                for row in rows:
                    anken_list.append({
                        'id': str(row[0]),  # UUID as string
                        'case_id': row[1],
                        'case_name': row[2],
                        'org_name': row[3],
                        'bidding_date': row[4].strftime('%Y-%m-%d') if row[4] else 'N/A',
                        'is_eligible': row[5],
                        'eligibility_reason': row[6],
                        'case_url': row[7],
                        'dashboard_url': f"{dashboard_url}/case/{row[0]}"
                    })
                    
    except Exception as e:
        logger.error(f"Failed to fetch anken information: {e}")
        
    return anken_list


def notify_success() -> None:
    """
    Send success notification to Slack with anken information.
    """
    # Get recent anken information
    anken_list = get_recent_anken_info()
    
    # Prepare summary statistics
    total_cases = len(anken_list)
    eligible_cases = sum(1 for a in anken_list if a['is_eligible'] is True)
    ineligible_cases = sum(1 for a in anken_list if a['is_eligible'] is False)
    
    # Build Slack message
    attachments = [{
        "color": "#36a64f",  # Green
        "pretext": ":white_check_mark: NJSS Crawler Execution Success",
        "title": "Today's New Procurement Cases",
        "fields": [
            {
                "title": "New Cases Crawled Today",
                "value": str(total_cases),
                "short": True
            },
            {
                "title": "Eligible Cases",
                "value": f"{eligible_cases} :white_check_mark:",
                "short": True
            },
            {
                "title": "Ineligible Cases",
                "value": f"{ineligible_cases} :x:",
                "short": True
            },
            {
                "title": "Crawl Date",
                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "short": True
            }
        ],
        "footer": "NJSS Procurement Automation",
        "ts": int(datetime.now().timestamp())
    }]
    
    # Add eligible cases information
    if eligible_cases > 0:
        eligible_text = "\n".join([
            f"• <{a['dashboard_url']}|{a['case_name'][:50]}...> - {a['org_name']} - {a['eligibility_reason'] or 'Eligible'}"
            for a in anken_list if a['is_eligible'] is True
        ][:10])  # Show up to 10 eligible cases
        
        attachments.append({
            "color": "#439FE0",  # Blue
            "title": "New Eligible Procurement Opportunities (Crawled Today)",
            "text": eligible_text,
            "footer": f"Showing {min(10, eligible_cases)} of {eligible_cases} eligible cases"
        })
    
    # Add ineligible cases information
    if ineligible_cases > 0:
        ineligible_text = "\n".join([
            f"• <{a['dashboard_url']}|{a['case_name'][:50]}...> - {a['org_name']} - {a['eligibility_reason'] or 'Ineligible'}"
            for a in anken_list if a['is_eligible'] is False
        ][:5])  # Show up to 5 ineligible cases
        
        attachments.append({
            "color": "#FF9999",  # Light red
            "title": "Ineligible Cases (For Reference)",
            "text": ineligible_text,
            "footer": f"Showing {min(5, ineligible_cases)} of {ineligible_cases} ineligible cases"
        })
    
    # Send notification
    send_slack_message({"attachments": attachments})


def notify_failure(context: Dict[str, Any]) -> None:
    """
    Send failure notification to Slack.
    
    Args:
        context: Airflow context dictionary
    """
    context["exception"] = context.get("exception", "Task failed")
    send_slack_notification(context)


def send_custom_notification(title: str, message: str, color: Optional[str] = "#439FE0") -> None:
    """
    Send a custom notification to Slack.
    
    Args:
        title: Notification title
        message: Notification message
        color: Slack attachment color (default: blue)
    """
    # Try to get Slack webhook URL from Airflow Variable first, then environment variable
    try:
        slack_webhook_url = Variable.get("slack_webhook_url")
    except KeyError:
        slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        logger.warning("Slack webhook URL not configured. Skipping notification.")
        return
    
    payload = {
        "attachments": [
            {
                "color": color,
                "title": title,
                "text": message,
                "footer": "Airflow Notification",
                "ts": int(datetime.now().timestamp())
            }
        ]
    }
    
    try:
        response = requests.post(
            slack_webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Custom Slack notification sent: {title}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send custom Slack notification: {e}")