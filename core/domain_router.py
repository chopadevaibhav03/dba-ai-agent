"""
Deterministic domain router for the AI assistant.

The router decides which operational domain a user request belongs to
before the request reaches Ollama.

Domains:
    linux
    oracle
    oscap
    general

IMPORTANT:
    This router does NOT use the LLM.

The purpose is to reduce the number of tools exposed to the local
Llama 3.2:3b model and improve inference performance.
"""

from __future__ import annotations

import re


LINUX_KEYWORDS = {
    "linux",
    "rhel",
    "red hat",
    "server",
    "cpu",
    "processor",
    "memory",
    "ram",
    "swap",
    "disk",
    "storage",
    "filesystem",
    "file system",
    "inode",
    "process",
    "processes",
    "load",
    "network",
    "interface",
    "interfaces",
    "port",
    "ports",
    "listening",
    "firewall",
    "selinux",
    "journal",
    "logs",
    "login",
    "logins",
    "ssh",
    "service",
    "services",
    "systemd",
    "kernel",
    "uptime",
    "users",
}


ORACLE_KEYWORDS = {
    "oracle",
    "database",
    "db",
    "cdb",
    "pdb",
    "pdbs",
    "instance",
    "tablespace",
    "tablespaces",
    "session",
    "sessions",
    "blocking",
    "blocked",
    "sql",
    "listener",
    "listener",
    "sid",
    "oracle database",
    "oracle instance",
}


OSCAP_KEYWORDS = {
    "oscap",
    "openscap",
    "xccdf",
    "scap",
    "cis",
    "compliance",
    "compliant",
    "compliance scan",
    "security scan",
    "security findings",
    "security finding",
    "vulnerability scan",
    "hardening",
    "harden",
    "benchmark",
    "benchmarking",
    "rule",
    "rules",
    "remediation",
    "finding",
    "findings",
    "security",
}


def _contains_keyword(text: str, keyword: str) -> bool:
    """
    Match keywords safely.

    For phrases such as "red hat" or "oracle database", substring
    matching is appropriate.

    For individual words, use word boundaries.
    """

    if " " in keyword:
        return keyword in text

    return bool(
        re.search(
            rf"\b{re.escape(keyword)}\b",
            text,
        )
    )


def _score_domain(text: str, keywords: set[str]) -> int:
    """
    Count matching domain keywords.
    """

    score = 0

    for keyword in keywords:
        if _contains_keyword(text, keyword):
            score += 1

    return score


def detect_domain(user_message: str) -> str:
    """
    Determine the most likely domain.

    Returns:
        "linux"
        "oracle"
        "oscap"
        "general"

    The router is intentionally conservative.

    If no operational domain is clearly indicated, the request is
    classified as general.
    """

    text = (user_message or "").strip().lower()

    if not text:
        return "general"

    scores = {
        "linux": _score_domain(text, LINUX_KEYWORDS),
        "oracle": _score_domain(text, ORACLE_KEYWORDS),
        "oscap": _score_domain(text, OSCAP_KEYWORDS),
    }

    # OSCAP gets priority when explicitly mentioned.
    #
    # Example:
    # "security findings from OSCAP"
    #
    # Both security and findings could match multiple domains, but
    # explicit OSCAP terminology should win.
    if "oscap" in text or "openscap" in text or "xccdf" in text:
        return "oscap"

    # Oracle gets priority when explicitly mentioned.
    if "oracle" in text:
        return "oracle"

    best_domain = max(
        scores,
        key=scores.get,
    )

    best_score = scores[best_domain]

    if best_score == 0:
        return "general"

    return best_domain


def route_prompt(user_message: str) -> dict:
    """
    Return routing information useful to the AI orchestrator.
    """

    domain = detect_domain(user_message)

    return {
        "domain": domain,
        "scores": {
            "linux": _score_domain(
                user_message.lower(),
                LINUX_KEYWORDS,
            ),
            "oracle": _score_domain(
                user_message.lower(),
                ORACLE_KEYWORDS,
            ),
            "oscap": _score_domain(
                user_message.lower(),
                OSCAP_KEYWORDS,
            ),
        },
    }


if __name__ == "__main__":
    tests = [
        "What is the current CPU usage?",
        "Why is my Linux server using so much memory?",
        "Is Oracle healthy?",
        "Are there any blocking sessions?",
        "Show my PDB status",
        "What are my OSCAP findings?",
        "Explain my CIS compliance findings",
        "What is the capital of India?",
    ]

    for question in tests:
        print(
            f"{question}\n"
            f"  -> {detect_domain(question)}"
        ) 