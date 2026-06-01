#!/usr/bin/env python3
"""
Parse Claude Code OpenTelemetry log files into human-readable format.

Usage:
    python log_parser.py <logfile> [output_format]

    output_format: 'summary' (default) | 'tools' | 'events'
"""

import re
import sys
from pathlib import Path
from typing import Any, cast


def _parse_content(content: str) -> dict[str, Any]:
    """
    Parse Claude Code log content and extract key information.

    Args:
        content: Log text content

    Returns:
        Dictionary containing prompt, models, tokens, costs, commands, lines_of_code
    """
    result = {
        "prompt": "",
        "models": [],
        "tokens": {},  # {model: {input, output, cacheRead}}
        "costs": {},  # {model: cost}
        "commands": [],  # list of executed commands
        "lines_of_code": {"added": 0, "removed": 0},
    }

    # Extract user prompt
    prompt_match = re.search(r"prompt:\s*'([^']+)'", content)
    if prompt_match:
        result["prompt"] = prompt_match.group(1)

    # Extract all models used (convert set to list for JSON serialization)
    result["models"] = sorted(set(re.findall(r"model:\s*'([\w.-]+)'", content)))

    # Extract token usage
    for model in result["models"]:
        pattern = rf"model:\s'{re.escape(model)}'.*?type:\s'(\w+)'.*?value:\s*(\d+)"
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            result["tokens"][model] = {}
            for token_type, value in matches:
                if token_type == "cacheRead":
                    token_type = "cache_read"
                current = result["tokens"][model].get(token_type, 0)
                result["tokens"][model][token_type] = max(current, int(value))

    # Extract costs
    cost_blocks = re.finditer(
        r"name:\s'claude_code\.cost\.usage'.*?(?=name:|\Z)", content, re.DOTALL
    )
    for block in cost_blocks:
        block_content = block.group(0)
        for model in result["models"]:
            pattern = rf"model:\s'{re.escape(model)}'.*?value:\s*([\d.]+)"
            matches = re.findall(pattern, block_content, re.DOTALL)
            if matches:
                result["costs"][model] = float(matches[-1])

    # Extract lines of code
    loc_pattern = r"name:\s'claude_code\.lines_of_code\.count'.*?type:\s'(\w+)'.*?value:\s*(\d+)"
    loc_matches = re.findall(loc_pattern, content, re.DOTALL)
    for loc_type, value in loc_matches:
        result["lines_of_code"][loc_type] = int(value)

    # Extract bash commands
    commands = re.findall(r'"full_command":"([^"]+)"', content)
    for cmd in commands:
        cmd = cmd.replace('\\"', '"')
        commands_list = cast(list[str], result["commands"])
        if cmd not in commands_list:
            commands_list.append(cmd)

    return result


def filter_user_output(raw_stdout: list[str] | str) -> str:
    """
    Filter OTel logs and extract user-visible output.

    OTel logs are multi-line JavaScript object format, starting from
    an independent '{' line to matching '}'.

    Args:
        raw_stdout: List of stdout lines or complete string

    Returns:
        Filtered user-visible output
    """
    if isinstance(raw_stdout, list):
        lines = raw_stdout
    else:
        lines = raw_stdout.split("\n")

    user_lines = []
    in_otel_block = False
    brace_depth = 0

    for line in lines:
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            continue

        # Detect OTel block start (independent '{' line)
        if stripped == "{" and not in_otel_block:
            in_otel_block = True
            brace_depth = 1
            continue

        # Inside OTel block
        if in_otel_block:
            # Track brace depth
            brace_depth += stripped.count("{") - stripped.count("}")
            # Block end
            if brace_depth <= 0:
                in_otel_block = False
            continue

        # Other filter rules (maintain backward compatibility)
        if stripped.startswith("LogRecord"):
            continue
        if stripped.startswith("Metric,"):
            continue
        if ",name:" in stripped and ",value:" in stripped:
            continue

        user_lines.append(line)

    return "\n".join(user_lines)


def parse_stdout_summary(raw_stdout: list[str] | str) -> dict[str, Any]:
    """
    Parse Claude Code stdout to extract session summary.

    Args:
        raw_stdout: List of stdout lines or complete string

    Returns:
        Dictionary containing prompt, models, tokens, costs, commands, lines_of_code
    """
    if isinstance(raw_stdout, list):
        content = "\n".join(raw_stdout)
    else:
        content = raw_stdout
    return _parse_content(content)


def parse_log(filepath):
    """Parse Claude Code log file and extract key information."""
    content = Path(filepath).read_text()
    return _parse_content(content)


def format_summary(data):
    """Format data as human-readable summary."""
    lines = []
    lines.append("=" * 70)
    lines.append("CLAUDE CODE SESSION SUMMARY")
    lines.append("=" * 70)
    lines.append("")

    # Prompt
    if data["prompt"]:
        prompt = data["prompt"]
        if len(prompt) > 68:
            prompt = prompt[:65] + "..."
        lines.append(f"PROMPT: {prompt}")
        lines.append("")

    # Models
    if data["models"]:
        lines.append(f"MODELS USED: {', '.join(sorted(data['models']))}")
        lines.append("")

    # Token usage
    lines.append("-" * 70)
    lines.append("TOKEN USAGE")
    lines.append("-" * 70)

    total_in, total_out, total_cache = 0, 0, 0

    for model in sorted(data["tokens"].keys()):
        tokens = data["tokens"][model]
        inp = tokens.get("input", 0)
        out = tokens.get("output", 0)
        cache = tokens.get("cache_read", 0)

        if inp or out or cache:
            lines.append(f"\n{model}:")
            if inp:
                lines.append(f"  Input:      {inp:,} tokens")
                total_in += inp
            if out:
                lines.append(f"  Output:     {out:,} tokens")
                total_out += out
            if cache:
                lines.append(f"  Cache Read: {cache:,} tokens")
                total_cache += cache

    if total_in or total_out:
        lines.append(f"\n{'─' * 50}")
        if total_in:
            lines.append(f"TOTAL Input:  {total_in:,} tokens")
        if total_out:
            lines.append(f"TOTAL Output: {total_out:,} tokens")
        if total_cache:
            lines.append(f"TOTAL Cache:  {total_cache:,} tokens")

    lines.append("")

    # Cost
    if data["costs"]:
        lines.append("-" * 70)
        lines.append("COST")
        lines.append("-" * 70)

        total_cost = 0
        for model in sorted(data["costs"].keys()):
            cost = data["costs"][model]
            if cost > 0:
                lines.append(f"  {model}: ${cost:.6f}")
                total_cost += cost

        lines.append(f"  {'─' * 50}")
        lines.append(f"  TOTAL: ${total_cost:.6f} USD")
        lines.append("")

    # Lines of code
    if data["lines_of_code"]["added"] or data["lines_of_code"]["removed"]:
        lines.append("-" * 70)
        lines.append("LINES OF CODE")
        lines.append("-" * 70)
        if data["lines_of_code"]["added"]:
            lines.append(f"  Added:   {data['lines_of_code']['added']:,} lines")
        if data["lines_of_code"]["removed"]:
            lines.append(f"  Removed: {data['lines_of_code']['removed']:,} lines")
        lines.append("")

    # Commands
    if data["commands"]:
        lines.append("-" * 70)
        lines.append(f"COMMANDS EXECUTED ({len(data['commands'])} unique)")
        lines.append("-" * 70)

        for i, cmd in enumerate(data["commands"], 1):
            display_cmd = cmd if len(cmd) <= 65 else cmd[:62] + "..."
            lines.append(f"  {i}. {display_cmd}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_tools_only(data):
    """Show only the commands."""
    lines = ["COMMANDS EXECUTED", "=" * 70]
    for i, cmd in enumerate(data["commands"], 1):
        lines.append(f"{i}. {cmd}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print("  python log_parser.py path/to/claude_stdout.txt")
        print("  python log_parser.py path/to/claude_stdout.txt tools")
        sys.exit(1)

    logfile = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else "summary"

    print(f"Parsing {logfile}...\n")

    try:
        data = parse_log(logfile)

        if output_format == "tools":
            print(format_tools_only(data))
        else:
            print(format_summary(data))

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
# mypy: disable-error-code="no-untyped-def,index"
