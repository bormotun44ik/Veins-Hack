ROLE_FOCUS = {
    "Senior Backend Engineer": {
        "primary_concerns": [
            "technical debt", "system reliability", "knowledge transfer", "on-call load"
        ],
        "manager_questions": [
            "Is there an active incident driving night work?",
            "Who else can pair on critical modules to reduce bus factor?",
            "Is 1:1 cadence appropriate (weekly vs bi-weekly)?",
            "Are deadlines realistic given current technical state?",
        ],
    },
    "Engineering Manager": {
        "primary_concerns": [
            "team velocity", "context switching", "1:1 quality",
            "stakeholder management", "OKR alignment"
        ],
        "manager_questions": [
            "How many direct reports? Is span of control sustainable?",
            "What % of time is in meetings vs deep work?",
            "Are 1:1 conversations going deeper than status updates?",
            "Who is helping with stakeholder pressure?",
        ],
    },
    "Tech Lead": {
        "primary_concerns": [
            "bandwidth", "mentorship vs IC work", "review load",
            "architectural decisions"
        ],
        "manager_questions": [
            "Is review queue clearing in <24h?",
            "Time split: code vs reviews vs mentorship?",
            "Anyone groomed to take over Tech Lead duties?",
        ],
    },
    "Backend Engineer": {
        "primary_concerns": [
            "technical execution", "code quality", "ownership clarity"
        ],
        "manager_questions": [
            "Are tasks clearly scoped?",
            "Has access to senior review on tough problems?",
            "What's blocking unblocking velocity?",
        ],
    },
    "Frontend Engineer": {
        "primary_concerns": [
            "UX quality", "design alignment", "performance"
        ],
        "manager_questions": [
            "Coordination with design — smooth or friction?",
            "Performance budget enforced?",
        ],
    },
    "Junior Frontend Engineer": {
        "primary_concerns": [
            "growth", "safety net", "feedback loops",
            "imposter syndrome risk", "learning curve"
        ],
        "manager_questions": [
            "Has dedicated mentor checking in weekly?",
            "Tasks in sweet spot — challenging but achievable?",
            "Psychological safety to ask 'dumb' questions?",
        ],
    },
    "QA Engineer": {
        "primary_concerns": [
            "coverage", "regression detection", "release confidence"
        ],
        "manager_questions": [
            "Test coverage trending up?",
            "Time between report and fix?",
            "QA included in design review?",
        ],
    },
}


def get_role_focus(role: str) -> dict:
    """Don't lie about role — return empty dict if unknown/empty,
    prompt builder will skip role_section entirely (no false context)."""
    if not role or role not in ROLE_FOCUS:
        return {}
    return ROLE_FOCUS[role]
