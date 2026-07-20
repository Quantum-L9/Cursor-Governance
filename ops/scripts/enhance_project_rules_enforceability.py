#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "OPS-PRE-001"
component_name: "Project Rules Enhancer"
layer: "operations"
domain: "governance"
type: "enhancer"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2026-01-04T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["re", "pathlib"]
integrates_with: ["EXE-VAL-001", "OPS-OPS-001"]
api_endpoints: []
data_sources: ["project_rules/*.md"]
outputs: ["Enhanced project rules files"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Enhance Project Rules files with enforceable language and mandatory checklists"
summary: "Converts suggestions to mandates, adds enforcement sections, and strengthens language"
business_value: "Ensures project rules are actionable and verifiable"
success_metrics: ["enhancement_rate >= 95%", "enforcement_coverage = 100%"]

# === TAGS & CLASSIFICATION ===
tags: ["rules", "enhancement", "enforcement", "governance", "automation"]
keywords: ["rules", "enhance", "enforce", "mandate", "checklist"]
related_components: ["EXE-VAL-001", "OPS-OPS-001"]

# === DESCRIPTION ===
Enhance existing Project Rules files with enforceable language and mandatory checklists.
Converts suggestions to mandates and adds verification requirements.
"""

import re
from pathlib import Path


class RuleEnhancer:
    """Enhance Project Rules with enforceable language"""

    def __init__(self, rules_dir: Path):
        self.rules_dir = Path(rules_dir)

    def enhance_file(self, file_path: Path) -> tuple[bool, str]:
        """Enhance a single rule file"""
        if not file_path.exists():
            return False, f"File not found: {file_path}"

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        enhanced = content

        # 1. Convert suggestions to mandates
        enhanced = self._convert_to_mandates(enhanced)

        # 2. Add enforcement section if missing
        if "## Enforcement" not in enhanced and "# Enforcement" not in enhanced:
            enhanced = self._add_enforcement_section(enhanced)

        # 3. Add verification checklist
        enhanced = self._add_verification_checklist(enhanced)

        # 4. Convert weak language to strong
        enhanced = self._strengthen_language(enhanced)

        if enhanced != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(enhanced)
            return True, "Enhanced"
        else:
            return False, "No changes needed"

    def _convert_to_mandates(self, content: str) -> str:
        """Convert suggestions to mandatory requirements"""
        lines = content.split("\n")
        enhanced_lines = []

        for line in lines:
            # Skip code blocks
            if line.strip().startswith("```"):
                enhanced_lines.append(line)
                continue

            # Convert "Always use" → "MUST use"
            line = re.sub(r"^(\s*)- Always use", r"\1- **MUST** use", line, flags=re.MULTILINE)
            line = re.sub(r"^(\s*)- Follow", r"\1- **MUST** follow", line, flags=re.MULTILINE)
            line = re.sub(r"^(\s*)- Use", r"\1- **MUST** use", line, flags=re.MULTILINE)
            line = re.sub(r"^(\s*)- Maintain", r"\1- **MUST** maintain", line, flags=re.MULTILINE)
            line = re.sub(r"^(\s*)- Include", r"\1- **MUST** include", line, flags=re.MULTILINE)

            # Convert "Never" → "MUST NOT"
            line = re.sub(r"^(\s*)- Never ", r"\1- **MUST NOT** ", line, flags=re.MULTILINE)
            line = re.sub(r"^(\s*)- Don\'t ", r"\1- **MUST NOT** ", line, flags=re.MULTILINE)
            line = re.sub(r"^(\s*)- Do not ", r"\1- **MUST NOT** ", line, flags=re.MULTILINE)

            # Convert "Should" → "MUST" (for critical rules)
            if any(
                keyword in line.lower() for keyword in ["mandatory", "required", "critical", "must"]
            ):
                line = re.sub(r"^(\s*)- Should ", r"\1- **MUST** ", line, flags=re.MULTILINE)

            # Convert "Avoid" → "MUST NOT"
            line = re.sub(r"^(\s*)- Avoid ", r"\1- **MUST NOT** ", line, flags=re.MULTILINE)

            enhanced_lines.append(line)

        return "\n".join(enhanced_lines)

    def _add_enforcement_section(self, content: str) -> str:
        """Add enforcement section if missing"""
        enforcement_section = """

## Enforcement

**This rule is MANDATORY and automatically enforced by Cursor AI.**

### How It's Enforced

- **Pre-Execution Check**: Cursor AI verifies compliance before code generation
- **Violation Detection**: Non-compliance triggers warnings and requires correction
- **Continuous Monitoring**: Rules apply throughout the entire session
- **Self-Verification**: AI must complete verification checklist before claiming completion

### Enforcement Level

- **MANDATORY**: Non-negotiable requirements (marked with MUST/MUST NOT)
- **REQUIRED**: Critical for compliance (marked with REQUIRED)
- **RECOMMENDED**: Best practices (marked with SHOULD)

### Consequences of Violation

- Code generation blocked until compliance
- Warning messages displayed
- Self-verification checklist required
- May trigger governance escalation

"""

        # Add before Related section or at end
        if "---\nRelated:" in content:
            content = content.replace("---\nRelated:", enforcement_section + "\n---\nRelated:")
        elif content.strip().endswith("---"):
            content = content.rstrip("---") + enforcement_section + "---"
        else:
            content += enforcement_section

        return content

    def _add_verification_checklist(self, content: str) -> str:
        """Add verification checklist for actionable rules"""
        # Only add if file has actionable rules (MUST statements)
        if "**MUST**" not in content and "MANDATORY" not in content.upper():
            return content

        checklist = """
### Verification Checklist

**Before proceeding, verify compliance:**

- [ ] All MUST requirements are met
- [ ] All MUST NOT prohibitions are avoided
- [ ] Required checklists are completed
- [ ] Evidence is available for verification
- [ ] Self-verification protocol followed

**If any checkbox is unchecked → STOP and fix before proceeding.**

"""

        # Add after Enforcement section or before Related
        if "## Enforcement" in content:
            content = content.replace("## Enforcement", "## Enforcement" + checklist)
        elif "---\nRelated:" in content:
            content = content.replace("---\nRelated:", checklist + "\n---\nRelated:")
        else:
            content += checklist

        return content

    def _strengthen_language(self, content: str) -> str:
        """Strengthen weak language to enforceable statements"""
        replacements = [
            (r"\bcan\b", "MUST", "MUST"),  # "can use" → "MUST use"
            (r"\bmay\b", "MUST", "MUST"),  # "may use" → "MUST use" (for critical)
            (r"\bshould\b", "MUST", "MUST"),  # "should use" → "MUST use" (for critical)
            (r"\bprefer\b", "MUST", "MUST"),  # "prefer" → "MUST" (for critical)
            (r"\bconsider\b", "MUST", "MUST"),  # "consider" → "MUST" (for critical)
        ]

        # Only strengthen in rule sections, not examples
        lines = content.split("\n")
        enhanced_lines = []
        in_code_block = False
        in_example = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                enhanced_lines.append(line)
                continue

            if "Example" in line or "example" in line.lower():
                in_example = True
            elif line.strip().startswith("##") or line.strip().startswith("#"):
                in_example = False

            if not in_code_block and not in_example:
                # Strengthen language in rule sections
                if any(
                    keyword in line.lower() for keyword in ["mandatory", "required", "critical"]
                ):
                    for pattern, old_word, new_word in replacements:
                        line = re.sub(pattern, new_word, line, flags=re.IGNORECASE)

            enhanced_lines.append(line)

        return "\n".join(enhanced_lines)

    def enhance_all(self):
        """Enhance all .mdc files in rules directory"""
        print("🔧 Enhancing Project Rules for Enforceability...")
        print(f"📂 Rules directory: {self.rules_dir}\n")

        mdc_files = list(self.rules_dir.rglob("*.mdc"))
        enhanced_count = 0

        for file_path in sorted(mdc_files):
            if file_path.name == "index.mdc":
                continue  # Skip index

            changed, status = self.enhance_file(file_path)
            if changed:
                enhanced_count += 1
                print(f"✅ Enhanced: {file_path.relative_to(self.rules_dir)}")

        print(f"\n{'='*60}")
        print("✅ Enhancement Complete!")
        print(f"   Files enhanced: {enhanced_count}/{len(mdc_files)-1}")
        print(f"{'='*60}")


if __name__ == "__main__":
    workspace = Path(
        "/Users/ib-mac/Dropbox/Prompt_Repo_IB/L9-Agent-Prompt-Insanity/L9 Reasoning Agent V1.0"
    )
    rules_dir = workspace / ".cursor" / "rules"

    enhancer = RuleEnhancer(rules_dir)
    enhancer.enhance_all()
