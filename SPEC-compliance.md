# COMPLIANCE.md

Compliance-as-Code checklist for automated validation. This document expresses governance as executable, versioned policy that agents can evaluate against the codebase.

> "Compliance drifts because systems move faster than checklists."

---

## Quick Reference

| Layer | Purpose | Tools |
|-------|---------|-------|
| Governance | Define requirements | This document |
| Policy | Express rules as code | Rego, YAML, Python validators |
| Execution | Automated CI/CD checks | GitHub Actions, pre-commit hooks |
| Evidence | Audit trail storage | Git history, logs, SIEM |

---

## 1. Secrets Management

### SEC-001: No Hardcoded Secrets
- [ ] No API keys in source code
- [ ] No passwords in configuration files
- [ ] No tokens in environment examples
- [ ] `.env` files listed in `.gitignore`

**Check command:**
```bash
grep -rE "(api_key|password|secret|token)\s*=\s*['\"][^'\"]+['\"]" --include="*.py" --include="*.ts" --include="*.js" .
```

### SEC-002: Secret Rotation Policy
- [ ] All secrets rotate every 90 days maximum
- [ ] Rotation events logged with timestamp
- [ ] No secrets older than rotation threshold

### SEC-003: Environment Variable Usage
- [ ] Production secrets loaded from environment
- [ ] Secret manager integration (Doppler, Vault, etc.)
- [ ] No secrets in CI/CD logs (masked in output)

---

## 2. Dependency Security

### DEP-001: Vulnerability Scanning
- [ ] No critical CVEs in dependencies
- [ ] No high-severity CVEs older than 30 days
- [ ] Automated scanning in CI pipeline

**Check commands:**
```bash
# Python
pip-audit

# Node.js
npm audit --audit-level=high
```

### DEP-002: Dependency Pinning
- [ ] All dependencies version-pinned
- [ ] Lock files committed (`requirements.txt`, `package-lock.json`, `pnpm-lock.yaml`)
- [ ] No floating versions in production

### DEP-003: License Compliance
- [ ] No GPL-licensed dependencies in proprietary code
- [ ] License inventory maintained
- [ ] Compatible licenses for distribution

---

## 3. Code Quality

### CODE-001: Static Analysis
- [ ] Linting passes without errors
- [ ] Type checking passes (mypy, TypeScript)
- [ ] No security warnings from static analyzers

**Check commands:**
```bash
# Python
ruff check .
mypy src/

# TypeScript
npx tsc --noEmit
```

### CODE-002: Test Coverage
- [ ] Minimum 70% code coverage for critical paths
- [ ] All public APIs have tests
- [ ] Integration tests for external service calls

### CODE-003: Documentation
- [ ] Public functions have docstrings
- [ ] API endpoints documented
- [ ] README explains setup and usage

---

## 4. Access Control

### ACCESS-001: Principle of Least Privilege
- [ ] API keys scoped to minimum required permissions
- [ ] Service accounts have limited access
- [ ] No admin credentials in application code

### ACCESS-002: Authentication
- [ ] All external endpoints require authentication
- [ ] JWT tokens validated and not expired
- [ ] Session timeouts configured

### ACCESS-003: Authorization
- [ ] Role-based access control implemented
- [ ] Sensitive operations require elevated permissions
- [ ] Access decisions logged

---

## 5. Data Protection

### DATA-001: PII Handling
- [ ] PII identified and classified
- [ ] PII encrypted at rest
- [ ] PII masked in logs

### DATA-002: Data Retention
- [ ] Retention policies defined
- [ ] Automated deletion of expired data
- [ ] Backup encryption enabled

### DATA-003: Input Validation
- [ ] All user input validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)

---

## 6. Infrastructure

### INFRA-001: Container Security
- [ ] Base images from trusted registries
- [ ] No root user in containers
- [ ] Images scanned for vulnerabilities

### INFRA-002: Network Security
- [ ] HTTPS enforced (no HTTP)
- [ ] TLS 1.2+ required
- [ ] Firewall rules documented

### INFRA-003: Logging & Monitoring
- [ ] Security events logged
- [ ] Logs shipped to central platform
- [ ] Alerting configured for anomalies

---

## 7. CI/CD Pipeline

### CICD-001: Pipeline Security
- [ ] Secrets injected at runtime (not in code)
- [ ] Build artifacts signed
- [ ] Deployment requires approval for production

### CICD-002: Branch Protection
- [ ] Main branch protected
- [ ] PRs require review
- [ ] Status checks must pass before merge

### CICD-003: Audit Trail
- [ ] All deployments logged
- [ ] Rollback capability verified
- [ ] Change history preserved

---

## 8. API Security

### API-001: Rate Limiting
- [ ] Rate limits configured for all endpoints
- [ ] Abuse prevention mechanisms active
- [ ] Rate limit responses follow standards (429)

### API-002: Error Handling
- [ ] No stack traces in production responses
- [ ] Error messages don't leak internal details
- [ ] Consistent error format

### API-003: Input/Output Validation
- [ ] Request schemas validated (Pydantic, Zod)
- [ ] Response schemas enforced
- [ ] Content-Type headers verified

---

## Automated Compliance Check

### Python Validator Script

```python
#!/usr/bin/env python3
"""
Compliance checker for automated validation.
Run: python compliance_check.py
"""

import subprocess
import sys
from pathlib import Path

CHECKS = [
    {
        "id": "SEC-001",
        "name": "No hardcoded secrets",
        "cmd": ["grep", "-rE", r"(api_key|password|secret|token)\s*=\s*['\"][^'\"]+['\"]",
                "--include=*.py", "."],
        "expect_failure": True,  # grep returns 1 when no matches (good)
    },
    {
        "id": "DEP-001",
        "name": "No critical vulnerabilities",
        "cmd": ["pip-audit", "--strict"],
        "expect_failure": False,
    },
    {
        "id": "CODE-001",
        "name": "Linting passes",
        "cmd": ["ruff", "check", "."],
        "expect_failure": False,
    },
]

def run_check(check: dict) -> bool:
    try:
        result = subprocess.run(
            check["cmd"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        passed = (result.returncode == 0) != check.get("expect_failure", False)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {check['id']}: {check['name']}")
        if not passed:
            print(f"       Output: {result.stdout or result.stderr}")
        return passed
    except FileNotFoundError:
        print(f"[SKIP] {check['id']}: {check['name']} (tool not found)")
        return True

def main():
    results = [run_check(c) for c in CHECKS]
    failed = sum(1 for r in results if not r)
    print(f"\n{'='*50}")
    print(f"Compliance: {len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
```

---

## Evidence Collection

For audit purposes, collect evidence of compliance:

| Control | Evidence Source | Retention |
|---------|-----------------|-----------|
| SEC-001 | Git commit scans | 1 year |
| DEP-001 | pip-audit/npm audit logs | 90 days |
| CODE-001 | CI pipeline logs | 90 days |
| ACCESS-001 | IAM policy exports | 1 year |
| CICD-002 | GitHub branch protection API | Real-time |

### Export Evidence

```bash
# Export branch protection settings
gh api repos/{owner}/{repo}/branches/main/protection > evidence/branch-protection.json

# Export recent security scans
pip-audit --format json > evidence/pip-audit-$(date +%Y%m%d).json

# Export dependency tree
pip freeze > evidence/requirements-$(date +%Y%m%d).txt
```

---

## Framework Mapping

| Control ID | SOC2 | ISO 27001 | GDPR |
|------------|------|-----------|------|
| SEC-001 | CC6.1 | A.9.4.3 | Art. 32 |
| SEC-002 | CC6.6 | A.9.2.4 | Art. 32 |
| DEP-001 | CC7.1 | A.12.6.1 | - |
| DATA-001 | CC6.5 | A.8.2.3 | Art. 5 |
| DATA-002 | CC6.5 | A.8.2.3 | Art. 17 |
| API-001 | CC6.6 | A.13.1.1 | - |

---

## Review Cadence

| Review Type | Frequency | Owner |
|-------------|-----------|-------|
| Automated checks | Every commit | CI/CD |
| Dependency scan | Weekly | Security Agent |
| Full compliance audit | Quarterly | GRC Team |
| Policy update | As needed | Engineering Lead |

---

## Remediation Workflow

1. **Detect** - Automated check fails in CI/CD
2. **Alert** - Notification sent to responsible party
3. **Triage** - Severity assessed (Critical/High/Medium/Low)
4. **Fix** - Code changes made to address issue
5. **Verify** - Automated check passes
6. **Document** - Evidence logged for audit trail

### SLA by Severity

| Severity | Response Time | Resolution Time |
|----------|---------------|-----------------|
| Critical | 1 hour | 24 hours |
| High | 4 hours | 72 hours |
| Medium | 24 hours | 7 days |
| Low | 72 hours | 30 days |

---

## Agent Integration

This checklist can be validated by a compliance robot agent:

```python
from crewai import Agent, Task

compliance_agent = Agent(
    role="Compliance Auditor",
    goal="Validate codebase against COMPLIANCE.md checklist",
    backstory="Security-focused agent that ensures code meets governance requirements",
    tools=[
        run_grep_check,
        run_pip_audit,
        run_linter,
        export_evidence,
    ]
)

audit_task = Task(
    description="Run all compliance checks and generate evidence report",
    agent=compliance_agent,
    expected_output="JSON report with pass/fail status for each control"
)
```

---

*Last updated: 2026-02-03*
*Version: 1.0.0*
