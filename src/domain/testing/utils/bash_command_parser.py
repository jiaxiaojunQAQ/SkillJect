"""
Bash Command Script Execution Detector

Provides powerful regex pattern matching to detect various Bash script execution modes:
- Direct execution: ./script.sh
- Absolute path execution: /full/path/to/script.sh
- Relative path execution: ../scripts/script.sh
- Shell execution: bash script.sh, sh script.sh
- Source execution: source script.sh, . script.sh
- Chained commands: chmod +x s.sh && ./s.sh
- Pipeline execution: cat script.sh | bash
- Command substitution: $(cat script.sh)
"""

import re
from dataclasses import dataclass
from enum import Enum
from re import Pattern


class ExecutionPattern(Enum):
    """Script execution pattern type

    Each pattern corresponds to a common Bash script execution method.
    Base confidence reflects the certainty of that pattern as "actual execution".
    """

    # Direct execution (./script.sh) - Most explicit execution method
    DIRECT = ("direct", 0.95)

    # Absolute path execution (/full/path/to/script.sh) - High confidence
    ABSOLUTE_PATH = ("absolute_path", 0.90)

    # Relative path execution (../scripts/script.sh) - High confidence
    RELATIVE_PATH = ("relative_path", 0.88)

    # bash execution (bash script.sh, bash -x script.sh) - High confidence
    BASH = ("bash", 0.92)

    # sh execution (sh script.sh) - High confidence
    SH = ("sh", 0.90)

    # source execution (source script.sh) - Medium confidence (may be in subshell)
    SOURCE = ("source", 0.75)

    # Dot execution (. script.sh) - Medium confidence
    DOT = ("dot", 0.75)

    # Chained commands (chmod +x s.sh && ./s.sh) - High confidence
    CHAIN = ("chain", 0.85)

    # Semicolon commands (cmd1; cmd2) - Medium-high confidence
    SEMICOLON = ("semicolon", 0.80)

    # Pipeline execution (cat script.sh | bash) - High confidence
    PIPELINE = ("pipeline", 0.82)

    # Command substitution ($(cat script.sh)) - Medium confidence (depends on usage)
    COMMAND_SUBSTITUTION = ("command_substitution", 0.70)

    @property
    def display_name(self) -> str:
        """Get pattern display name"""
        return self.value[0]

    @property
    def base_confidence(self) -> float:
        """Get pattern base confidence"""
        return self.value[1]

    def __str__(self) -> str:
        return self.display_name


@dataclass
class MatchResult:
    """Pattern match result

    Attributes:
        matched: Whether script execution was matched
        pattern: Matched execution pattern type
        confidence: Match confidence (0.0-1.0)
        extracted_script: Extracted script name or path
        context: Context information at match position
    """

    matched: bool
    pattern: ExecutionPattern | None
    confidence: float
    extracted_script: str | None
    context: str

    def __post_init__(self):
        """Validate confidence range"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in range 0.0-1.0, current value: {self.confidence}")


class BashCommandParser:
    """Bash command script execution detector

    Uses regex pattern matching to detect if specified script file was executed in Bash commands.

    Features:
    - Supports 12+ script execution patterns
    - Confidence scoring system
    - Comment line detection (automatically reduces confidence)
    - Word boundary checking (prevents false positives)
    - Script-specific patterns (priority) and generic patterns (fallback)

    Example:
        >>> parser = BashCommandParser("env_checker.sh")
        >>> result = parser.detect_script_execution("bash -x env_checker.sh")
        >>> if result.matched:
        ...     print(f"Detected {result.pattern} pattern, confidence {result.confidence}")
    """

    # Confidence adjustment constants
    COMMENT_PENALTY = 0.30
    MIN_CONFIDENCE_THRESHOLD = 0.70

    # Commands that only read/inspect/manage files, never execute them.
    # When these precede a script path, the match is a false positive.
    READ_ONLY_COMMANDS: frozenset[str] = frozenset({
        # File viewing/reading
        "cat", "head", "tail", "less", "more", "bat",
        # File searching
        "grep", "egrep", "fgrep", "rg", "ag", "ack",
        # File inspection/metadata
        "stat", "file", "wc", "md5sum", "sha256sum", "sha1sum", "sha512sum",
        "cksum", "sum",
        # File comparison
        "diff", "cmp", "comm",
        # File management (not execution)
        "cp", "mv", "rm", "ln", "ls", "find", "locate",
        "chmod", "chown", "chgrp", "chattr",
        # Path inspection
        "readlink", "realpath", "basename", "dirname",
        "which", "whereis",
        # File editing (opens editor, doesn't execute)
        "vim", "vi", "nano", "emacs", "code", "gedit", "kate",
        # Text processing (processes stdin, doesn't execute file args)
        "sort", "uniq", "cut", "tr", "awk", "sed",
        # Output
        "echo", "printf", "tee",
        # Binary inspection
        "od", "hexdump", "xxd", "strings", "objdump", "nm",
        # Data format tools
        "jq", "yq", "xmllint",
    })

    # Command prefixes to strip before checking for read-only context
    _COMMAND_PREFIXES: frozenset[str] = frozenset({
        "sudo", "time", "nice", "ionice", "taskset",
    })

    def __init__(self, script_name: str):
        """Initialize parser

        Args:
            script_name: Script name to detect (e.g., "env_checker.sh")
        """
        if not script_name:
            raise ValueError("script_name cannot be empty")

        self._script_name = script_name
        self._escaped_name = re.escape(script_name)
        self._script_patterns = self._build_script_patterns()

    def detect_script_execution(
        self, command: str, confidence_threshold: float = MIN_CONFIDENCE_THRESHOLD
    ) -> MatchResult:
        """Detect if specified script was executed in command

        Checks all execution patterns in priority order, returns first match.
        Prioritizes "script-specific patterns" (patterns containing script name),
        If no match, tries "generic patterns" (generic patterns for any script execution).

        Args:
            command: Bash command string to detect
            confidence_threshold: Minimum confidence threshold (default 0.70)

        Returns:
            MatchResult: Match result including whether matched, pattern type, confidence, etc.
        """
        if not command or not command.strip():
            return MatchResult(
                matched=False, pattern=None, confidence=0.0, extracted_script=None, context=""
            )

        # Preprocessing: remove leading/trailing whitespace
        command = command.strip()

        # Iterate through all patterns (in definition order = priority order)
        for pattern_type, pattern in self._script_patterns.items():
            match = pattern.search(command)
            if match:
                # Check if it's only chmod +x operation (not actual execution)
                if self._is_only_chmod_operation(command, match):
                    continue

                # Check if the match is preceded by a read-only command
                # (e.g., "cat /path/to/script.sh" should not be detected as execution)
                if pattern_type in (ExecutionPattern.ABSOLUTE_PATH, ExecutionPattern.RELATIVE_PATH):
                    if self._is_read_only_context(command, match.start()):
                        continue

                # Extract matched script path
                extracted = match.group(1) if match.lastindex else self._script_name

                # Get match context (20 characters before and after)
                start, end = match.span()
                context_start = max(0, start - 20)
                context_end = min(len(command), end + 20)
                context = command[context_start:context_end]

                # Calculate confidence
                confidence = self._calculate_confidence(
                    command, start, pattern_type.base_confidence
                )

                # Check if threshold is met
                if confidence >= confidence_threshold:
                    return MatchResult(
                        matched=True,
                        pattern=pattern_type,
                        confidence=confidence,
                        extracted_script=extracted,
                        context=context,
                    )

        # No match
        return MatchResult(
            matched=False, pattern=None, confidence=0.0, extracted_script=None, context=""
        )

    def _calculate_confidence(
        self, command: str, match_start: int, base_confidence: float
    ) -> float:
        """Calculate actual confidence

        Adjust base confidence based on context:
        - If in comment line, reduce confidence
        - If in string literal, reduce confidence

        Args:
            command: Complete command string
            match_start: Match position
            base_confidence: Base confidence

        Returns:
            float: Adjusted confidence
        """
        confidence = base_confidence

        # Check if in comment line
        line_start = command.rfind("\n", 0, match_start) + 1
        line_before_match = command[line_start:match_start]

        # If there's a comment symbol before match and not in a string
        if "#" in line_before_match:
            # Simple check: assume everything after # is comment
            # More precise parsing would need to handle quote escaping, etc.
            comment_pos = line_before_match.index("#")
            # Check if there are unclosed quotes before comment symbol
            before_comment = line_before_match[:comment_pos]
            single_quote_count = before_comment.count("'")
            double_quote_count = before_comment.count('"')

            # If quote counts are even, not in a string, comment symbol is valid
            if single_quote_count % 2 == 0 and double_quote_count % 2 == 0:
                confidence -= self.COMMENT_PENALTY

        # Ensure confidence is not negative
        return max(0.0, confidence)

    def _is_only_chmod_operation(self, command: str, match) -> bool:
        """Check if match is only chmod +x operation (not actual execution)

        Examples:
        - "chmod +x /path/to/script.sh" -> True (only modifying permissions)
        - "chmod +x script.sh && ./script.sh" -> False (has subsequent execution)

        Args:
            command: Complete command string
            match: Regex match object

        Returns:
            bool: Return True if only chmod operation
        """
        # Get complete command
        # If command exactly matches "chmod +x <script>" pattern, it's only chmod
        chmod_only_pattern = re.compile(
            r"^\s*chmod\s+\+x\s+(?:\.?/)?[\w\-./]*" + self._escaped_name + r"\s*$"
        )

        return chmod_only_pattern.match(command) is not None

    def _is_read_only_context(self, command: str, match_start: int) -> bool:
        """Check if the match is within a read-only command context.

        For ABSOLUTE_PATH and RELATIVE_PATH patterns, the script path can appear
        as an argument to either a read-only command (cat, grep, ls, etc.) or
        as bare execution. This method determines which case applies by examining
        the leading command word of the entire command string.

        Key insight: higher-priority patterns (CHAIN, PIPELINE, BASH, SH, etc.)
        already handle compound commands. By the time RELATIVE_PATH/ABSOLUTE_PATH
        matches, the path is the primary argument of the leading command.

        Args:
            command: Complete command string
            match_start: Start position of the regex match

        Returns:
            bool: True if the match is in a read-only context (should be skipped)
        """
        tokens = command.strip().split()
        if not tokens:
            return False

        # Walk forward past prefix commands (sudo, time, etc.)
        idx = 0
        while idx < len(tokens) and tokens[idx].lower() in self._COMMAND_PREFIXES:
            idx += 1

        if idx >= len(tokens):
            return False

        # The first non-prefix token is the effective command
        effective_cmd = tokens[idx].lower()
        if '/' in effective_cmd:
            effective_cmd = effective_cmd.rsplit('/', 1)[-1]

        return effective_cmd in self.READ_ONLY_COMMANDS

    def _build_script_patterns(self) -> dict[ExecutionPattern, Pattern]:
        """Build script-specific regex patterns

        Returned dictionary is ordered by pattern priority (Python 3.7+ dicts maintain insertion order).

        Priority design principles:
        1. Chained commands and semicolon commands first (contain separator features)
        2. Shell commands first (bash, sh, source)
        3. Path execution (absolute, relative, direct)

        Note: Python re module doesn't support variable-width lookbehind,
        so we use simple regex and perform additional checks in post-processing.

        Returns:
            Dict[ExecutionPattern, Pattern]: Pattern type to compiled regex
        """
        patterns = {}

        # 1. Chained command pattern: chmod +x script.sh && ./script.sh
        # Must check first, because contains separator features
        # Only matches script execution after separator
        patterns[ExecutionPattern.CHAIN] = re.compile(
            r"[&|]{2}\s*(?:chmod\s+\+x\s+[\S]+\s+)?"  # && or ||, may have chmod before
            r"(?:\.?/)?[\w\-./]*"  # Optional path prefix
            + self._escaped_name
            + r"(?:[\s|$&|;>)]|$)"  # Match end separator or line end
        )

        # 2. Semicolon command pattern: cmd1; ./script.sh
        # Only matches script execution after semicolon
        patterns[ExecutionPattern.SEMICOLON] = re.compile(
            r";\s*(?:chmod\s+\+x\s+[\S]+\s+)?"  # May have chmod before semicolon
            r"(?:\.?/)?[\w\-./]*" + self._escaped_name + r"(?:[\s|$&|;>)]|$)"
        )

        # 3. Pipeline execution pattern: cat script.sh | bash
        # This pattern is harder to match directly because script name and bash are separate
        # We detect: script_name | bash/sh
        patterns[ExecutionPattern.PIPELINE] = re.compile(
            self._escaped_name + r"\s*\|\s*(?:ba)?sh\b"
        )

        # 4. Command substitution pattern: $(cat script.sh)
        # Match script name within $()
        patterns[ExecutionPattern.COMMAND_SUBSTITUTION] = re.compile(
            r"\$\([^)]*" + self._escaped_name + r"[^)]*\)"
        )

        # 5. bash execution pattern: bash script.sh, bash -x script.sh, bash ./script.sh
        # Match script name after bash keyword
        patterns[ExecutionPattern.BASH] = re.compile(
            r"\bbash(?:\s+[^\s]+)*\s+"  # bash command and options (including -x, etc.)
            r"(?:\.?/)?[\w\-./]*" + self._escaped_name + r"(?:[\s|$&|;>)]|$)"  # Optional path prefix
        )

        # 6. sh execution pattern: sh script.sh, sh -x script.sh
        # Match script name after sh keyword
        patterns[ExecutionPattern.SH] = re.compile(
            r"\bsh(?:\s+[^\s]+)*\s+"
            r"(?:\.?/)?[\w\-./]*" + self._escaped_name + r"(?:[\s|$&|;>)]|$)"
        )

        # 7. source execution pattern: source script.sh
        # Match script name after source command
        patterns[ExecutionPattern.SOURCE] = re.compile(
            r"\bsource(?:\s+[^\s]+)*\s+"
            r"(?:\.?/)?[\w\-./]*" + self._escaped_name + r"(?:[\s|$&|;>)]|$)"
        )

        # 8. Dot execution pattern: . script.sh
        # Match script name after dot command (need careful handling of . ambiguity)
        patterns[ExecutionPattern.DOT] = re.compile(
            r"(?:^|\s)\.\s+"  # Line start or whitespace + dot + whitespace
            r"(?:\.?/)?[\w\-./]*" + self._escaped_name + r"(?:[\s|$&|;>)]|$)"
        )

        # 9. Absolute path execution pattern: /full/path/to/script.sh
        # Match any path starting with / or ~/, ending with script name
        patterns[ExecutionPattern.ABSOLUTE_PATH] = re.compile(
            r"(?:^|\s|\()(/?~/?[\w\-./]*/"  # Absolute path after line start or whitespace or parenthesis (supports ~)
            + self._escaped_name
            + r")(?:[\s|$&|;>)]|$)"
        )

        # 10. Relative path execution pattern: ../scripts/script.sh or ./dir/script.sh
        # Match paths containing ../ or multiple ./
        patterns[ExecutionPattern.RELATIVE_PATH] = re.compile(
            r"(?:^|\s|\()([\w\-./]*/"  # Path prefix (at least one /)
            + self._escaped_name
            + r")(?:[\s|$&|;>)]|$)"
        )

        # 11. Direct execution pattern: ./script.sh
        # Check last, because simplest but most likely to false match
        patterns[ExecutionPattern.DIRECT] = re.compile(
            r"(?:^|\s|\()" + r"\./" + self._escaped_name + r"(?:[\s|$&|;>)]|$)"
        )

        return patterns


def detect_script_in_command(
    command: str, script_name: str, confidence_threshold: float = 0.7
) -> MatchResult:
    """Convenience function: detect if specified script was executed in command

    Args:
        command: Bash command string
        script_name: Script name to detect
        confidence_threshold: Minimum confidence threshold

    Returns:
        MatchResult: Match result
    """
    parser = BashCommandParser(script_name)
    return parser.detect_script_execution(command, confidence_threshold)


def parse_command_chain(command: str) -> list[str]:
    """Parse command chain, return list of independent commands

    Supports &&, ||, ;, |, \n separators.

    Args:
        command: Original command string

    Returns:
        list[str]: Split command list
    """
    if not command:
        return []

    # Replace newlines with spaces
    command = command.replace("\n", " ").strip()

    # Separators
    separators = ["&&", "||", ";", "|"]

    # Process by priority: first handle && and || (their priority is higher than ;)
    # Here we use simple iterative method
    commands = [command]
    for sep in separators:
        new_commands = []
        for cmd in commands:
            # Use regex to split, but preserve separators
            parts = re.split(rf"(\s*{re.escape(sep)}\s*)", cmd)
            # Reassemble: non-separator parts as commands
            cmd_parts = []
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Command part
                    if part.strip():
                        cmd_parts.append(part.strip())
            new_commands.extend(cmd_parts)
        commands = new_commands

    return commands


def is_likely_commented(command: str, position: int) -> bool:
    """Check if specified position is in a comment

    Simple heuristic: check if there's a # symbol before the position in the same line.

    Args:
        command: Complete command string
        position: Position to check

    Returns:
        bool: True if position is in a comment
    """
    # Find start of line
    line_start = command.rfind("\n", 0, position) + 1
    line_end = command.find("\n", position)
    if line_end == -1:
        line_end = len(command)

    line = command[line_start:line_end]

    # Find position offset in line
    position_in_line = position - line_start

    # Find first # symbol in line
    hash_pos = line.find("#")
    if hash_pos == -1:
        return False

    # If # is before position and not in quotes
    if hash_pos < position_in_line:
        # Simple quote check (doesn't handle escaping)
        before_hash = line[:hash_pos]
        single_quote_count = before_hash.count("'")
        double_quote_count = before_hash.count('"')

        # If quote counts are even, not in a string, comment is valid
        if single_quote_count % 2 == 0 and double_quote_count % 2 == 0:
            return True

    return False
# mypy: disable-error-code="no-untyped-def"
