"""Pattern Matcher - Regex-based Pattern Matching.

Provides high-performance pattern matching with context extraction
and support for multiple patterns.
"""

import logging
from typing import List

from .models import PatternDefinition, PatternMatch

logger = logging.getLogger(__name__)


class PatternMatcher:
    """High-performance regex-based pattern matcher.

    Matches patterns against text and extracts context information.
    Optimized for processing large volumes of text with multiple patterns.

    Example:
        >>> matcher = PatternMatcher()
        >>> matches = matcher.match(text, pattern)
        >>> matches_all = matcher.match_all(text, [p1, p2, p3])
    """

    def match(
        self, text: str, pattern: PatternDefinition
    ) -> List[PatternMatch]:
        """Match a single pattern against text.

        Args:
            text: Text to search
            pattern: Pattern definition to match

        Returns:
            List of pattern matches found

        Example:
            >>> pattern = PatternDefinition(...)
            >>> matches = matcher.match("CVE-2021-44228 found", pattern)
            >>> len(matches)
            1
        """
        matches: List[PatternMatch] = []

        # Use compiled pattern for performance
        regex = pattern.compiled

        for match_obj in regex.finditer(text):
            # Extract matched text and position
            matched_text = match_obj.group(0)
            start_pos = match_obj.start()
            end_pos = match_obj.end()

            # Extract named capture groups
            captured_groups = match_obj.groupdict()
            if not captured_groups:
                captured_groups = None

            # Determine output value (use first capture group or full match)
            output_value = matched_text
            if captured_groups and pattern.capture_groups:
                # Use first named group as primary value
                first_group = next(iter(captured_groups.values()), None)
                if first_group is not None:
                    output_value = first_group

            # Extract surrounding context
            context = self.extract_context(text, start_pos, end_pos)

            # Create match object
            pattern_match = PatternMatch(
                pattern_id=pattern.id,
                pattern_name=pattern.name,
                domain=pattern.domain,
                category=pattern.category,
                matched_text=matched_text,
                start_position=start_pos,
                end_position=end_pos,
                output_type=pattern.output_type,
                output_value=output_value,
                captured_groups=captured_groups,
                base_confidence=pattern.base_confidence,
                final_confidence=pattern.base_confidence,
                surrounding_context=context,
            )

            matches.append(pattern_match)

        logger.debug(
            "Pattern matching complete",
            extra={
                "pattern_name": pattern.name,
                "matches_found": len(matches),
                "text_length": len(text),
            },
        )

        return matches

    def match_all(
        self, text: str, patterns: List[PatternDefinition]
    ) -> List[PatternMatch]:
        """Match multiple patterns against text.

        Args:
            text: Text to search
            patterns: List of pattern definitions to match

        Returns:
            Combined list of all matches from all patterns

        Example:
            >>> patterns = [pattern1, pattern2, pattern3]
            >>> all_matches = matcher.match_all(text, patterns)
        """
        all_matches: List[PatternMatch] = []

        for pattern in patterns:
            matches = self.match(text, pattern)
            all_matches.extend(matches)

        logger.debug(
            "Multi-pattern matching complete",
            extra={
                "patterns_count": len(patterns),
                "total_matches": len(all_matches),
                "text_length": len(text),
            },
        )

        return all_matches

    def extract_context(
        self, text: str, start: int, end: int, window: int = 100
    ) -> str:
        """Extract surrounding context for a match.

        Args:
            text: Full text
            start: Start position of match
            end: End position of match
            window: Number of characters to include on each side

        Returns:
            Context string with match in the middle

        Example:
            >>> context = matcher.extract_context(text, 50, 65, window=20)
            >>> # Returns ~40 chars with match in center
        """
        # Calculate context boundaries
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)

        # Extract context
        context = text[context_start:context_end]

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."

        return context
