"""
Self-Correction Loops

Enables the agent to evaluate its own outputs and retry with different approaches:
- Define success criteria for tasks
- Evaluate outputs against criteria
- Automatic retry with modified approaches on failure
- Learn from failed attempts within session
- Track correction history for debugging

This makes the agent more robust and able to recover from mistakes.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple
from enum import Enum


class CorrectionStatus(Enum):
    """Status of a correction attempt."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class SuccessCriteria:
    """Defines what constitutes success for a task."""
    description: str
    check_function: Optional[Callable[[str], bool]] = None
    required_patterns: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    must_contain_tool_result: bool = False
    custom_validator: Optional[Callable[[str, Dict], Tuple[bool, str]]] = None


@dataclass
class CorrectionAttempt:
    """Record of a single correction attempt."""
    attempt_number: int
    approach: str
    input_prompt: str
    output: str
    status: CorrectionStatus
    evaluation_notes: str
    duration_ms: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class CorrectionSession:
    """Tracks all correction attempts for a single task."""
    task_description: str
    criteria: SuccessCriteria
    attempts: List[CorrectionAttempt] = field(default_factory=list)
    max_attempts: int = 3
    final_status: Optional[CorrectionStatus] = None
    successful_approach: Optional[str] = None


class SelfCorrector:
    """
    Manages self-correction loops for the agent.

    The corrector evaluates outputs against criteria and suggests
    alternative approaches when the initial attempt fails.
    """

    def __init__(self, max_attempts: int = 3, verbose: bool = False):
        """
        Initialize the self-corrector.

        Args:
            max_attempts: Maximum correction attempts per task
            verbose: Whether to print correction details
        """
        self.max_attempts = max_attempts
        self.verbose = verbose
        self.correction_history: List[CorrectionSession] = []
        self.learned_patterns: Dict[str, List[str]] = {}  # task_type -> successful approaches

    def evaluate_output(
        self,
        output: str,
        criteria: SuccessCriteria,
        context: Dict[str, Any] = None
    ) -> Tuple[CorrectionStatus, str]:
        """
        Evaluate an output against success criteria.

        Args:
            output: The output to evaluate
            criteria: Success criteria to check against
            context: Optional context for evaluation

        Returns:
            Tuple of (status, evaluation_notes)
        """
        notes = []
        passed_checks = 0
        total_checks = 0

        # Check required patterns
        if criteria.required_patterns:
            total_checks += 1
            missing = [p for p in criteria.required_patterns if p.lower() not in output.lower()]
            if missing:
                notes.append(f"Missing required patterns: {missing}")
            else:
                passed_checks += 1
                notes.append("All required patterns found")

        # Check forbidden patterns
        if criteria.forbidden_patterns:
            total_checks += 1
            found = [p for p in criteria.forbidden_patterns if p.lower() in output.lower()]
            if found:
                notes.append(f"Found forbidden patterns: {found}")
            else:
                passed_checks += 1
                notes.append("No forbidden patterns found")

        # Check length constraints
        if criteria.min_length is not None:
            total_checks += 1
            if len(output) < criteria.min_length:
                notes.append(f"Output too short: {len(output)} < {criteria.min_length}")
            else:
                passed_checks += 1

        if criteria.max_length is not None:
            total_checks += 1
            if len(output) > criteria.max_length:
                notes.append(f"Output too long: {len(output)} > {criteria.max_length}")
            else:
                passed_checks += 1

        # Check for tool result
        if criteria.must_contain_tool_result:
            total_checks += 1
            if "TOOL_RESULT:" in output:
                passed_checks += 1
                notes.append("Contains tool result")
            else:
                notes.append("Missing tool result")

        # Custom check function
        if criteria.check_function:
            total_checks += 1
            try:
                if criteria.check_function(output):
                    passed_checks += 1
                    notes.append("Custom check passed")
                else:
                    notes.append("Custom check failed")
            except Exception as e:
                notes.append(f"Custom check error: {e}")

        # Custom validator with context
        if criteria.custom_validator and context:
            total_checks += 1
            try:
                valid, msg = criteria.custom_validator(output, context)
                if valid:
                    passed_checks += 1
                    notes.append(f"Validator passed: {msg}")
                else:
                    notes.append(f"Validator failed: {msg}")
            except Exception as e:
                notes.append(f"Validator error: {e}")

        # Determine overall status
        evaluation = "; ".join(notes) if notes else "No checks defined"

        if total_checks == 0:
            return CorrectionStatus.SKIPPED, "No criteria to check"

        ratio = passed_checks / total_checks

        if ratio == 1.0:
            return CorrectionStatus.SUCCESS, evaluation
        elif ratio >= 0.5:
            return CorrectionStatus.PARTIAL, evaluation
        else:
            return CorrectionStatus.FAILURE, evaluation

    def suggest_alternative_approach(
        self,
        task: str,
        failed_approaches: List[str],
        failure_notes: str
    ) -> str:
        """
        Suggest an alternative approach based on previous failures.

        Args:
            task: Description of the task
            failed_approaches: List of approaches that have been tried
            failure_notes: Notes about why previous attempts failed

        Returns:
            Suggested alternative approach prompt
        """
        # Check learned patterns for this type of task
        task_type = self._categorize_task(task)
        successful_approaches = self.learned_patterns.get(task_type, [])

        suggestions = []

        # Add learned successful approaches
        if successful_approaches:
            suggestions.append(f"Previously successful approach: {successful_approaches[-1]}")

        # Analyze failure patterns
        if "too short" in failure_notes.lower():
            suggestions.append("Provide more detailed and comprehensive response")

        if "too long" in failure_notes.lower():
            suggestions.append("Be more concise and focused")

        if "missing" in failure_notes.lower():
            suggestions.append("Ensure all required elements are included")

        if "forbidden" in failure_notes.lower():
            suggestions.append("Avoid restricted patterns or content")

        if "tool" in failure_notes.lower():
            suggestions.append("Use appropriate tools to complete the task")

        # Build alternative prompt
        prompt_parts = [
            f"Previous attempts failed. Failures: {failure_notes}",
            f"Tried approaches: {', '.join(failed_approaches)}",
            "",
            "Try a different approach:",
        ]

        if suggestions:
            prompt_parts.extend([f"- {s}" for s in suggestions])
        else:
            prompt_parts.append("- Think step by step about what went wrong")
            prompt_parts.append("- Try a completely different strategy")

        prompt_parts.append("")
        prompt_parts.append(f"Task: {task}")

        return "\n".join(prompt_parts)

    def _categorize_task(self, task: str) -> str:
        """Categorize a task for pattern matching."""
        task_lower = task.lower()

        if any(word in task_lower for word in ['read', 'show', 'display', 'list']):
            return 'read_task'
        elif any(word in task_lower for word in ['write', 'create', 'add', 'insert']):
            return 'write_task'
        elif any(word in task_lower for word in ['edit', 'modify', 'update', 'change']):
            return 'edit_task'
        elif any(word in task_lower for word in ['delete', 'remove']):
            return 'delete_task'
        elif any(word in task_lower for word in ['search', 'find', 'grep']):
            return 'search_task'
        elif any(word in task_lower for word in ['run', 'execute', 'command']):
            return 'execute_task'
        elif any(word in task_lower for word in ['analyze', 'explain', 'describe']):
            return 'analyze_task'
        else:
            return 'general_task'

    def record_success(self, task: str, approach: str):
        """Record a successful approach for learning."""
        task_type = self._categorize_task(task)
        if task_type not in self.learned_patterns:
            self.learned_patterns[task_type] = []

        # Keep only last 5 successful approaches per type
        self.learned_patterns[task_type].append(approach)
        if len(self.learned_patterns[task_type]) > 5:
            self.learned_patterns[task_type].pop(0)

    def create_session(
        self,
        task: str,
        criteria: SuccessCriteria
    ) -> CorrectionSession:
        """Create a new correction session for a task."""
        session = CorrectionSession(
            task_description=task,
            criteria=criteria,
            max_attempts=self.max_attempts
        )
        self.correction_history.append(session)
        return session

    def add_attempt(
        self,
        session: CorrectionSession,
        approach: str,
        input_prompt: str,
        output: str,
        duration_ms: int,
        context: Dict[str, Any] = None
    ) -> CorrectionAttempt:
        """
        Add and evaluate a correction attempt.

        Args:
            session: The correction session
            approach: Description of the approach used
            input_prompt: The prompt sent
            output: The output received
            duration_ms: How long the attempt took
            context: Optional context for evaluation

        Returns:
            The recorded attempt
        """
        status, notes = self.evaluate_output(output, session.criteria, context)

        attempt = CorrectionAttempt(
            attempt_number=len(session.attempts) + 1,
            approach=approach,
            input_prompt=input_prompt,
            output=output,
            status=status,
            evaluation_notes=notes,
            duration_ms=duration_ms
        )

        session.attempts.append(attempt)

        # Update session status
        if status == CorrectionStatus.SUCCESS:
            session.final_status = CorrectionStatus.SUCCESS
            session.successful_approach = approach
            self.record_success(session.task_description, approach)
        elif len(session.attempts) >= session.max_attempts:
            # Max attempts reached
            best = max(session.attempts, key=lambda a:
                (1 if a.status == CorrectionStatus.PARTIAL else 0))
            session.final_status = best.status

        if self.verbose:
            print(f"  [Correction] Attempt {attempt.attempt_number}: {status.value}")
            print(f"  [Correction] Notes: {notes}")

        return attempt

    def should_retry(self, session: CorrectionSession) -> bool:
        """Check if we should retry the task."""
        if session.final_status == CorrectionStatus.SUCCESS:
            return False
        if len(session.attempts) >= session.max_attempts:
            return False
        return True

    def get_session_summary(self, session: CorrectionSession) -> Dict[str, Any]:
        """Get a summary of a correction session."""
        return {
            "task": session.task_description,
            "total_attempts": len(session.attempts),
            "final_status": session.final_status.value if session.final_status else "in_progress",
            "successful_approach": session.successful_approach,
            "attempts": [
                {
                    "number": a.attempt_number,
                    "status": a.status.value,
                    "notes": a.evaluation_notes,
                    "duration_ms": a.duration_ms
                }
                for a in session.attempts
            ]
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall self-correction statistics."""
        if not self.correction_history:
            return {"sessions": 0, "message": "No correction sessions recorded"}

        total_sessions = len(self.correction_history)
        successful = sum(1 for s in self.correction_history
                        if s.final_status == CorrectionStatus.SUCCESS)
        partial = sum(1 for s in self.correction_history
                     if s.final_status == CorrectionStatus.PARTIAL)
        failed = sum(1 for s in self.correction_history
                    if s.final_status == CorrectionStatus.FAILURE)

        total_attempts = sum(len(s.attempts) for s in self.correction_history)
        avg_attempts = total_attempts / total_sessions if total_sessions > 0 else 0

        first_try_success = sum(1 for s in self.correction_history
                               if s.attempts and s.attempts[0].status == CorrectionStatus.SUCCESS)

        return {
            "sessions": total_sessions,
            "successful": successful,
            "partial": partial,
            "failed": failed,
            "success_rate": successful / total_sessions if total_sessions > 0 else 0,
            "total_attempts": total_attempts,
            "avg_attempts_per_task": avg_attempts,
            "first_try_success_rate": first_try_success / total_sessions if total_sessions > 0 else 0,
            "learned_patterns": {k: len(v) for k, v in self.learned_patterns.items()}
        }


# Pre-defined criteria for common tasks
def create_file_operation_criteria() -> SuccessCriteria:
    """Criteria for file operation tasks."""
    return SuccessCriteria(
        description="File operation must complete successfully",
        required_patterns=["successfully", "created", "written", "read"],
        forbidden_patterns=["error", "failed", "not found", "permission denied"],
        must_contain_tool_result=True
    )


def create_search_criteria() -> SuccessCriteria:
    """Criteria for search tasks."""
    return SuccessCriteria(
        description="Search must return relevant results",
        forbidden_patterns=["no matches", "error"],
        must_contain_tool_result=True,
        min_length=50  # Expect some results
    )


def create_code_execution_criteria() -> SuccessCriteria:
    """Criteria for code execution tasks."""
    return SuccessCriteria(
        description="Code must execute without errors",
        forbidden_patterns=["error:", "exception:", "traceback", "failed"],
        must_contain_tool_result=True
    )


def create_analysis_criteria(min_words: int = 50) -> SuccessCriteria:
    """Criteria for analysis/explanation tasks."""
    return SuccessCriteria(
        description=f"Analysis must be comprehensive (at least {min_words} words)",
        min_length=min_words * 5,  # Rough chars estimate
        forbidden_patterns=["i don't know", "unable to", "cannot"]
    )


# Convenience function for the orchestrator
def with_self_correction(
    corrector: SelfCorrector,
    task: str,
    execute_fn: Callable[[str], Tuple[str, int]],
    criteria: SuccessCriteria = None
) -> Tuple[str, CorrectionSession]:
    """
    Execute a task with self-correction.

    Args:
        corrector: The SelfCorrector instance
        task: Task description/prompt
        execute_fn: Function that takes prompt and returns (output, duration_ms)
        criteria: Optional custom criteria (auto-detected if not provided)

    Returns:
        Tuple of (final_output, correction_session)
    """
    # Auto-detect criteria if not provided
    if criteria is None:
        task_lower = task.lower()
        if any(word in task_lower for word in ['read', 'write', 'create', 'delete', 'edit']):
            criteria = create_file_operation_criteria()
        elif any(word in task_lower for word in ['search', 'find', 'grep']):
            criteria = create_search_criteria()
        elif any(word in task_lower for word in ['run', 'execute']):
            criteria = create_code_execution_criteria()
        else:
            criteria = create_analysis_criteria()

    session = corrector.create_session(task, criteria)
    current_prompt = task
    final_output = ""

    while corrector.should_retry(session):
        approach = f"Attempt {len(session.attempts) + 1}: {current_prompt[:100]}..."

        output, duration_ms = execute_fn(current_prompt)
        final_output = output

        attempt = corrector.add_attempt(
            session=session,
            approach=approach,
            input_prompt=current_prompt,
            output=output,
            duration_ms=duration_ms
        )

        if attempt.status == CorrectionStatus.SUCCESS:
            break

        # Generate alternative approach for next attempt
        failed_approaches = [a.approach for a in session.attempts]
        current_prompt = corrector.suggest_alternative_approach(
            task,
            failed_approaches,
            attempt.evaluation_notes
        )

    return final_output, session
