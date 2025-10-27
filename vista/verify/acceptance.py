import re
from typing import Any, Dict, Optional, List

class Acceptance:
    def __init__(self, lines: List[str]):
        self.lines = [l.strip() for l in lines if l.strip()]

    def perf_threshold_ms(self) -> Optional[int]:
        """Extract performance threshold from acceptance criteria"""
        patterns = [
            r"(?:p95|latency|response.time)\s*[<≤]\s*(\d+)\s*ms",  # p95 < 200ms
            r"(\d+)\s*ms\s*(?:p95|latency)",                      # 200ms p95
            r"performance.*(\d+)\s*ms"                            # performance under 200ms
        ]

        for line in self.lines:
            for pattern in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    return int(matches[0])
        return None

    def no_critical_vulns(self) -> bool:
        """Check if acceptance requires no critical vulnerabilities"""
        critical_patterns = [
            "no critical vulnerab",
            "zero critical findings",
            "no high severity issues",
            "security scan clean",
            "pass security review"
        ]

        for line in self.lines:
            if any(pattern in line.lower() for pattern in critical_patterns):
                return True
        return False

    def has_security_requirements(self) -> bool:
        """Check for any security requirements"""
        security_indicators = [
            "security", "vulnerab", "scan", "audit", "pen test",
            "owasp", "injection", "xss", "csrf", "ssl", "tls"
        ]

        for line in self.lines:
            if any(indicator in line.lower() for indicator in security_indicators):
                return True
        return False

    def get_quality_gates(self) -> Dict[str, Any]:
        """Extract all quality gates from acceptance criteria"""
        return {
            "performance_threshold_ms": self.perf_threshold_ms(),
            "no_critical_vulnerabilities": self.no_critical_vulns(),
            "has_security_requirements": self.has_security_requirements()
        }
