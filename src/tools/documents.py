"""
Document Processing Tools

Gemini can process various document formats:
- PDF: Up to 1,000 pages or 50MB, extracts tables, charts, diagrams
- Excel: Up to 100MB, interprets data, identifies patterns
- Word: Recognizes headings, tables, charts, footnotes
- CSV: Data analysis and transformation
- Google Docs/Sheets/Slides also supported

Capabilities:
- Structured data extraction (invoices, forms)
- Visual layout comprehension
- Q&A based on document content
- Summarization
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, List, Dict


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Supported document formats with their limits
DOCUMENT_FORMATS = {
    '.pdf': {'max_pages': 1000, 'max_size_mb': 50},
    '.xlsx': {'max_size_mb': 100},
    '.xls': {'max_size_mb': 100},
    '.docx': {'max_size_mb': 50},
    '.doc': {'max_size_mb': 50},
    '.csv': {'max_size_mb': 50},
    '.txt': {'max_size_mb': 10},
    '.rtf': {'max_size_mb': 20},
}


def get_git_bash() -> Optional[Path]:
    """Find Git Bash on Windows."""
    if sys.platform != 'win32':
        return None
    paths = [
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
        Path("C:/Program Files/Git/bin/bash.exe"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def call_gemini(query: str, account: int = 1, timeout: int = 180) -> Tuple[bool, str]:
    """Call Gemini with appropriate timeout for document processing."""
    if not GEMINI_SCRIPT.exists():
        return False, f"gemini-account.sh not found"

    try:
        if sys.platform == 'win32':
            git_bash = get_git_bash()
            if not git_bash:
                return False, "Git Bash not found"
            cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query]
        else:
            cmd = ["bash", str(GEMINI_SCRIPT), str(account), query]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Error: {error}"

        response = result.stdout.strip()
        return bool(response), response or "Empty response"

    except subprocess.TimeoutExpired:
        return False, "Timeout - document processing may take longer for large files"
    except Exception as e:
        return False, f"Error: {e}"


def process_document(
    document_path: str,
    query: str,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Process and analyze a document using Gemini.

    Args:
        document_path: Path to the document file
        query: Question or task to perform on the document
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, result: str)
    """
    path = Path(document_path).expanduser().resolve()

    if not path.exists():
        return False, f"Document not found: {document_path}"

    suffix = path.suffix.lower()
    if suffix not in DOCUMENT_FORMATS:
        return False, f"Unsupported document format: {suffix}. Supported: {list(DOCUMENT_FORMATS.keys())}"

    # Check file size
    file_size_mb = path.stat().st_size / (1024 * 1024)
    max_size = DOCUMENT_FORMATS[suffix].get('max_size_mb', 50)
    if file_size_mb > max_size:
        return False, f"File too large: {file_size_mb:.1f}MB (max {max_size}MB for {suffix})"

    prompt = f"""Process this document: {path}

Query: {query}

Analyze the document and provide a detailed response to the query.
Consider all content including:
- Text content
- Tables and structured data
- Charts and diagrams (if PDF)
- Headers, footers, and metadata

Provide comprehensive results based on the document content."""

    return call_gemini(prompt, account, timeout=300)


def extract_tables(
    document_path: str,
    output_format: str = "markdown",
    table_index: int = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Extract tables from a document.

    Args:
        document_path: Path to the document
        output_format: "markdown", "csv", or "json"
        table_index: Specific table to extract (1-indexed), or None for all
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, tables: str)
    """
    path = Path(document_path).expanduser().resolve()

    if not path.exists():
        return False, f"Document not found: {document_path}"

    table_spec = f"Extract table #{table_index}" if table_index else "Extract all tables"

    format_instructions = {
        "markdown": "Format each table as a Markdown table with headers",
        "csv": "Format each table as CSV with proper escaping",
        "json": "Format each table as JSON array of objects (headers as keys)"
    }

    prompt = f"""Document: {path}

{table_spec}

{format_instructions.get(output_format, format_instructions['markdown'])}

For each table:
1. Table number/identifier
2. Caption or context (if available)
3. The table data in {output_format} format
4. Number of rows and columns

Preserve data types where apparent (numbers, dates, percentages)."""

    return call_gemini(prompt, account, timeout=180)


def summarize_document(
    document_path: str,
    summary_type: str = "executive",
    max_length: int = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Generate a summary of a document.

    Args:
        document_path: Path to the document
        summary_type: "executive", "detailed", "bullet_points", "abstract"
        max_length: Optional maximum word count
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, summary: str)
    """
    path = Path(document_path).expanduser().resolve()

    if not path.exists():
        return False, f"Document not found: {document_path}"

    length_note = f"Keep the summary under {max_length} words." if max_length else ""

    summary_instructions = {
        "executive": "Create an executive summary suitable for busy stakeholders. Focus on key findings, decisions needed, and critical information.",
        "detailed": "Create a comprehensive summary covering all major sections and topics. Include important details and supporting information.",
        "bullet_points": "Create a bullet-point summary with key takeaways organized by topic.",
        "abstract": "Create an academic-style abstract covering purpose, methods, results, and conclusions."
    }

    prompt = f"""Document: {path}

{summary_instructions.get(summary_type, summary_instructions['executive'])}
{length_note}

Structure the summary clearly and highlight the most important information."""

    return call_gemini(prompt, account, timeout=180)


def extract_form_data(
    document_path: str,
    form_type: str = "auto",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Extract structured data from forms (invoices, applications, etc.).

    Args:
        document_path: Path to the form document
        form_type: Type hint ("invoice", "receipt", "application", "contract", "auto")
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, extracted_data: str)
    """
    path = Path(document_path).expanduser().resolve()

    if not path.exists():
        return False, f"Document not found: {document_path}"

    form_hints = {
        "invoice": "Extract: vendor info, invoice number, date, line items, subtotal, tax, total, payment terms",
        "receipt": "Extract: merchant, date, items purchased, quantities, prices, total, payment method",
        "application": "Extract: applicant info, contact details, qualifications, responses to questions",
        "contract": "Extract: parties involved, effective date, terms, obligations, signatures",
        "auto": "Detect the form type and extract all relevant structured fields"
    }

    prompt = f"""Document: {path}

This appears to be a {form_type} form.

{form_hints.get(form_type, form_hints['auto'])}

Extract all data into a structured format:
```json
{{
  "form_type": "detected type",
  "fields": {{
    "field_name": "value",
    ...
  }},
  "line_items": [...] (if applicable),
  "totals": {{...}} (if applicable),
  "metadata": {{
    "confidence": "high/medium/low",
    "notes": "any extraction notes"
  }}
}}
```

Be thorough and extract all visible information."""

    return call_gemini(prompt, account, timeout=180)


def compare_documents(
    doc_path_1: str,
    doc_path_2: str,
    comparison_focus: str = "content",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Compare two documents and highlight differences.

    Args:
        doc_path_1: Path to first document
        doc_path_2: Path to second document
        comparison_focus: "content", "structure", "data", or "all"
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, comparison: str)
    """
    path1 = Path(doc_path_1).expanduser().resolve()
    path2 = Path(doc_path_2).expanduser().resolve()

    if not path1.exists():
        return False, f"Document not found: {doc_path_1}"
    if not path2.exists():
        return False, f"Document not found: {doc_path_2}"

    focus_instructions = {
        "content": "Focus on textual content differences - changed, added, or removed text",
        "structure": "Focus on structural differences - sections, headings, organization",
        "data": "Focus on data/numerical differences - changed values, calculations",
        "all": "Compare all aspects - content, structure, data, and formatting"
    }

    prompt = f"""Compare these two documents:
Document 1: {path1}
Document 2: {path2}

{focus_instructions.get(comparison_focus, focus_instructions['all'])}

Provide:
1. Summary of key differences
2. Detailed change list (additions, deletions, modifications)
3. Sections that remain unchanged
4. Assessment of significance of changes
5. Any version/revision information detected"""

    return call_gemini(prompt, account, timeout=240)


def analyze_spreadsheet(
    spreadsheet_path: str,
    analysis_type: str = "overview",
    sheet_name: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Analyze Excel/CSV spreadsheet data.

    Args:
        spreadsheet_path: Path to spreadsheet file
        analysis_type: "overview", "statistics", "trends", "anomalies"
        sheet_name: Specific sheet to analyze (for Excel)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, analysis: str)
    """
    path = Path(spreadsheet_path).expanduser().resolve()

    if not path.exists():
        return False, f"Spreadsheet not found: {spreadsheet_path}"

    sheet_note = f"\nFocus on sheet: {sheet_name}" if sheet_name else "\nAnalyze the primary/first sheet"

    analysis_prompts = {
        "overview": """Provide an overview of the spreadsheet:
1. Number of rows and columns
2. Column headers and data types
3. Summary of what the data represents
4. Data quality assessment (missing values, inconsistencies)""",

        "statistics": """Perform statistical analysis:
1. Descriptive statistics for numerical columns (mean, median, std, min, max)
2. Frequency distributions for categorical columns
3. Correlations between numerical variables
4. Key statistical insights""",

        "trends": """Identify trends and patterns:
1. Time-based trends (if date column exists)
2. Growth/decline patterns
3. Seasonality or cyclical patterns
4. Outliers and their context
5. Predictive observations""",

        "anomalies": """Detect anomalies and issues:
1. Outliers in numerical data
2. Inconsistent data formats
3. Missing or null values
4. Duplicate records
5. Logical inconsistencies
6. Data entry errors"""
    }

    prompt = f"""Spreadsheet: {path}
{sheet_note}

{analysis_prompts.get(analysis_type, analysis_prompts['overview'])}

Provide detailed analysis with specific examples from the data."""

    return call_gemini(prompt, account, timeout=180)


def query_document_section(
    document_path: str,
    section_identifier: str,
    query: str,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Query a specific section of a document.

    Args:
        document_path: Path to document
        section_identifier: Section name, page number, or heading
        query: Question about the section
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, answer: str)
    """
    path = Path(document_path).expanduser().resolve()

    if not path.exists():
        return False, f"Document not found: {document_path}"

    prompt = f"""Document: {path}

Navigate to section: {section_identifier}

Query about this section: {query}

Provide:
1. Direct answer to the query
2. Relevant quotes or data from the section
3. Context from surrounding sections if helpful
4. Page/section reference for verification"""

    return call_gemini(prompt, account)


# Tool registry
DOCUMENT_TOOLS = {
    "process_document": process_document,
    "extract_tables": extract_tables,
    "summarize_document": summarize_document,
    "extract_form_data": extract_form_data,
    "compare_documents": compare_documents,
    "analyze_spreadsheet": analyze_spreadsheet,
    "query_document_section": query_document_section,
}
