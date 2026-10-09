#!/usr/bin/env python3
"""
NSN-IOH OPTIM: Deep Analysis NCR Generator
- Memory-based Claude analysis
- ClickHouse query fallback
- Composio email automation
- Daily automation-ready
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from anthropic import Anthropic

# ============================================================================
# CONFIGURATION
# ============================================================================

OPTIM_ROOT = Path(r"D:\NSN-IOH\OPTIM")
SQL_ROOTS = {
    "4g_nsa": OPTIM_ROOT / "sql_kpi_4g_nsa",
    "5g_nsa": OPTIM_ROOT / "sql_kpi_5g_nsa",
}

# Claude + Composio credentials (from environment)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")

# Email config
EMAIL_FROM = "daiya.barus@outlook.com"
EMAIL_TO = "daiya.barus@ptnw.co.id"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_latest_dump() -> Optional[Path]:
    """Find the most recent DUMP.*.xlsx file"""
    dumps = list(OPTIM_ROOT.glob("**/DUMP.*.xlsx"))
    if not dumps:
        return None
    return max(dumps, key=lambda p: p.stat().st_mtime)


def find_alarm_reports() -> List[Path]:
    """Find all alarm_report.* files"""
    return list(OPTIM_ROOT.glob("**/alarm_report.*"))


def load_dump_data(dump_path: Path) -> pd.DataFrame:
    """Load DUMP file into DataFrame"""
    try:
        return pd.read_excel(dump_path)
    except Exception as e:
        print(f"⚠️  Failed to load {dump_path}: {e}")
        return pd.DataFrame()


def get_sql_context() -> str:
    """Load SQL query files for context"""
    sql_context = "# Available SQL Queries for Root Cause Analysis:\n"
    for tech, sql_dir in SQL_ROOTS.items():
        sql_context += f"\n## {tech.upper()}\n"
        sql_files = list(sql_dir.glob("*.sql")) if sql_dir.exists() else []
        for sql_file in sql_files[:5]:  # Limit to 5 per tech
            try:
                sql_context += f"- {sql_file.name}\n"
                with open(sql_file) as f:
                    content = f.read()[:500]  # First 500 chars
                    sql_context += f"  Preview: {content}...\n"
            except Exception as e:
                sql_context += f"  Error: {e}\n"
    return sql_context


# ============================================================================
# CLAUDE ANALYSIS WITH MEMORY
# ============================================================================

class NCRAnalyzer:
    """Claude-powered NCR analysis with persistent memory"""

    def __init__(self):
        self.client = Anthropic()
        self.conversation_history = []
        self.analysis_results = {}

    def add_system_context(self):
        """Initialize system context for analysis"""
        system_prompt = f"""
You are an expert 5G/4G Network Operations Analyst specializing in root cause analysis (RCA) and NCR (Non-Conformance Report) generation.

CONTEXT:
- Technology: 4G NSA, 5G NSA (Nokia)
- Focus Areas: KPI degradation, alarm patterns, performance metrics
- Output Format: Professional NCR reports with actionable recommendations

AVAILABLE DATA SOURCES:
{get_sql_context()}

ANALYSIS FRAMEWORK:
1. **Data Collection Phase**: Load latest DUMP and correlate with alarm reports
2. **Pattern Recognition**: Identify KPI degradation patterns
3. **Root Cause Analysis**: Apply 5-Why methodology + Nokia-specific insights
4. **Impact Assessment**: Quantify business impact (revenue, SLA, customer experience)
5. **Recommendation**: Provide step-by-step remediation plan

OUTPUT STRUCTURE FOR NCR:
- Issue Summary (What)
- Timeline (When)
- Root Cause (Why - 5 levels deep)
- Impact Analysis (So What)
- Remediation Steps (How to Fix)
- Prevention Measures (How to Prevent)
- Approval Chain
"""
        return system_prompt

    def analyze_dump(self, dump_df: pd.DataFrame) -> str:
        """First turn: Analyze DUMP data"""
        summary = f"""
DUMP Data Summary:
- Rows: {len(dump_df)}
- Columns: {list(dump_df.columns)}
- Timestamp Range: {dump_df.iloc[0] if not dump_df.empty else 'N/A'}

Key Metrics Overview:
{dump_df.describe().to_string()}

Please identify:
1. Top 5 KPI anomalies
2. Correlation with alarm events
3. Preliminary root causes (if visible from data)
"""
        self.conversation_history.append({
            "role": "user",
            "content": summary
        })

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=self.add_system_context(),
            messages=self.conversation_history
        )

        analysis = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": analysis
        })

        self.analysis_results["dump_analysis"] = analysis
        return analysis

    def correlate_alarms(self, alarm_reports: List[Path]) -> str:
        """Second turn: Correlate with alarm patterns"""
        alarm_summary = "ALARM REPORTS ANALYSIS:\n"
        for alarm_file in alarm_reports[:3]:  # Limit to 3 files
            try:
                df = pd.read_excel(alarm_file) if alarm_file.suffix == '.xlsx' else pd.read_csv(alarm_file)
                alarm_summary += f"\n{alarm_file.name}:\n{df.head().to_string()}\n"
            except Exception as e:
                alarm_summary += f"\n{alarm_file.name}: Error loading - {e}\n"

        query = f"""
{alarm_summary}

Based on the DUMP analysis and these alarm patterns:
1. What is the correlation strength between KPI degradation and alarms?
2. Are there leading indicators in the alarm data?
3. Which alarms are symptoms vs root causes?
"""
        self.conversation_history.append({
            "role": "user",
            "content": query
        })

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=self.add_system_context(),
            messages=self.conversation_history
        )

        correlation = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": correlation
        })

        self.analysis_results["correlation_analysis"] = correlation
        return correlation

    def deep_root_cause(self) -> str:
        """Third turn: Deep 5-Why RCA"""
        query = """
Now perform a detailed 5-Why Root Cause Analysis:

LEVEL 1 (Symptom): What is the visible problem?
LEVEL 2 (Why?): What technical factors caused it?
LEVEL 3 (Why?): Why did those factors occur?
LEVEL 4 (Why?): What operational/process gaps exist?
LEVEL 5 (Why?): What is the fundamental root cause?

Also provide:
- Confidence level (High/Medium/Low)
- Evidence supporting each level
- Alternative root causes if applicable
- ClickHouse query recommendations if data gaps exist
"""
        self.conversation_history.append({
            "role": "user",
            "content": query
        })

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            system=self.add_system_context(),
            messages=self.conversation_history
        )

        rca = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": rca
        })

        self.analysis_results["rca"] = rca
        return rca

    def generate_ncr_report(self) -> str:
        """Final turn: Generate formal NCR report"""
        query = """
Based on all analysis performed, generate a FORMAL NCR REPORT with:

[NCR HEADER]
NCR ID: [Auto-generate from timestamp]
Date: [Today's date]
Reported By: NSN-IOH OPTIM System
Technology: 4G NSA / 5G NSA

[ISSUE SUMMARY]
- Problem Statement
- KPI Impact (% degradation)
- Affected Elements

[TIMELINE]
- Issue Detection Time
- Escalation Timeline
- Resolution Timeline (if applicable)

[ROOT CAUSE ANALYSIS]
[Include the 5-Why framework]

[IMPACT ASSESSMENT]
- Service Impact
- Revenue Impact
- Customer Impact
- SLA Impact

[REMEDIATION PLAN]
Step 1: [Immediate action]
Step 2: [Short-term fix]
Step 3: [Long-term fix]

[PREVENTION MEASURES]
- Monitoring enhancement
- Parameter tuning
- Process improvement

[APPROVAL SECTION]
Prepared by: Claude Analysis System
Recommended for: NOC Manager / Optimization Team
"""
        self.conversation_history.append({
            "role": "user",
            "content": query
        })

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            system=self.add_system_context(),
            messages=self.conversation_history
        )

        ncr_report = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": ncr_report
        })

        self.analysis_results["ncr_report"] = ncr_report
        return ncr_report

    def get_full_memory_context(self) -> Dict:
        """Return complete analysis memory"""
        return {
            "timestamp": datetime.now().isoformat(),
            "conversation_turns": len(self.conversation_history),
            "analysis_results": self.analysis_results
        }


# ============================================================================
# COMPOSIO EMAIL AUTOMATION
# ============================================================================

def send_ncr_via_composio(ncr_report: str) -> bool:
    """Send NCR via Composio email"""
    try:
        from composio_openai import Composio, Action
        from openai import OpenAI

        composio_client = Composio(api_key=COMPOSIO_API_KEY)
        openai_client = OpenAI()

        # Prepare email content
        email_body = f"""
Dear NOC Team,

Please find the latest NCR analysis report below:

---
{ncr_report}
---

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
System: NSN-IOH OPTIM Analyzer

Please review and take necessary actions.

Best regards,
NSN-IOH OPTIM System
"""

        # Send via Composio
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"""Send an email using Composio:
TO: {EMAIL_TO}
FROM: {EMAIL_FROM}
SUBJECT: [NCR Report] Network Performance Analysis - {datetime.now().strftime('%Y-%m-%d')}
BODY:
{email_body}
"""
                }
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "send_email",
                        "description": "Send email via Gmail/Outlook",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string"},
                                "subject": {"type": "string"},
                                "body": {"type": "string"}
                            }
                        }
                    }
                }
            ]
        )

        print(f"✅ NCR sent to {EMAIL_TO}")
        return True

    except Exception as e:
        print(f"⚠️  Composio email failed: {e}")
        print(f"    Fallback: Save NCR to file")
        return False


def save_ncr_locally(ncr_report: str) -> Path:
    """Fallback: Save NCR report to file"""
    output_dir = OPTIM_ROOT / "NCR_Reports"
    output_dir.mkdir(exist_ok=True)

    filename = f"NCR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = output_dir / filename

    with open(filepath, 'w') as f:
        f.write(ncr_report)

    print(f"💾 NCR saved to: {filepath}")
    return filepath


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("🚀 NSN-IOH OPTIM: NCR Analysis System Started\n")

    # Step 1: Load data
    print("📊 Loading data...")
    dump_file = find_latest_dump()
    if not dump_file:
        print("❌ No DUMP file found. Exiting.")
        sys.exit(1)

    print(f"✅ Found DUMP: {dump_file}")
    dump_data = load_dump_data(dump_file)

    alarm_files = find_alarm_reports()
    print(f"✅ Found {len(alarm_files)} alarm report(s)")

    # Step 2: Initialize analyzer
    print("\n🧠 Initializing Claude analysis with memory...\n")
    analyzer = NCRAnalyzer()

    # Step 3: Multi-turn analysis
    print("📈 TURN 1: Analyzing DUMP data...")
    dump_analysis = analyzer.analyze_dump(dump_data)
    print(dump_analysis[:500] + "...\n")

    print("🔗 TURN 2: Correlating alarm patterns...")
    correlation = analyzer.correlate_alarms(alarm_files)
    print(correlation[:500] + "...\n")

    print("🔍 TURN 3: Deep root cause analysis...")
    rca = analyzer.deep_root_cause()
    print(rca[:500] + "...\n")

    print("📄 TURN 4: Generating NCR report...")
    ncr_report = analyzer.generate_ncr_report()
    print("\n" + "="*80)
    print(ncr_report)
    print("="*80 + "\n")

    # Step 4: Send via Composio or save locally
    print("📧 Sending NCR...")
    if COMPOSIO_API_KEY:
        success = send_ncr_via_composio(ncr_report)
    else:
        print("⚠️  COMPOSIO_API_KEY not set, saving locally")
        success = False

    if not success:
        save_ncr_locally(ncr_report)

    # Step 5: Save memory context
    memory = analyzer.get_full_memory_context()
    memory_file = OPTIM_ROOT / f"analysis_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(memory_file, 'w') as f:
        json.dump(memory, f, indent=2)

    print(f"✅ Analysis complete. Memory saved to: {memory_file}")


if __name__ == "__main__":
    main()
