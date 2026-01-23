#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-MIG-001"
component_name: "Project Rules Migration Script"
layer: "operations"
domain: "migration"
type: "migration_tool"
status: "active"
created: "2025-11-20T10:00:00Z"
updated: "2025-11-20T10:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

Migrates .cursorrules to Cursor Project Rules format (.cursor/rules/*.mdc)
Ensures all rules are enforceable with imperative language and clear checklists.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class RuleSection:
    """Represents a rule section to be migrated"""
    title: str
    content: str
    category: str
    filename: str
    enforceability_score: int
    dependencies: List[str]

class ProjectRulesMigrator:
    """Migrates .cursorrules to Project Rules format"""
    
    def __init__(self, workspace_root: Path = None):
        if workspace_root is None:
            workspace_root = Path.cwd()
        
        self.workspace = Path(workspace_root)
        self.cursor_rules_dir = self.workspace / ".cursor" / "rules"
        self.template_file = self.workspace / ".cursor-commands" / "templates" / ".cursorrules"
        
        # Define rule mappings: (section_pattern, category, filename, enforceability_enhancements)
        self.rule_mappings = [
            # Core Governance
            (r"## Core Governance Principles", "core", "governance-core.mdc", [
                "MUST use Suite 6 canonical headers",
                "MUST follow kebab-case naming",
                "MUST integrate with formal logic system",
                "MUST maintain audit trails"
            ]),
            (r"## File Standards", "core", "file-standards.mdc", [
                "MUST have canonical headers",
                "MUST follow component ID pattern",
                "MUST be self-documenting"
            ]),
            (r"## Development Workflow", "core", "development-workflow.mdc", [
                "MUST use @.cursor-commands/ for access",
                "MUST validate compliance before commits",
                "MUST follow 10-step reasoning framework"
            ]),
            
            # Code Standards
            (r"## Code & Technical Standards", "core", "code-standards.mdc", [
                "MUST NOT use emojis in production code",
                "MUST NOT include placeholders",
                "MUST use .env.template for secrets",
                "MUST tag confidence scores"
            ]),
            
            # Behavior
            (r"## Communication Style", "behavior", "communication-style.mdc", [
                "MUST use direct, system-architect tone",
                "MUST be production-ready by default",
                "MUST minimize meta-commentary"
            ]),
            (r"## Agent Behavior Expectations", "behavior", "ai-behavior.mdc", [
                "MUST retain corrections across sessions",
                "MUST minimize back-and-forth",
                "MUST complete tasks fully",
                "MUST use FACT-FIRST APPROACH"
            ]),
            (r"## Agent Behavior Modes", "behavior", "behavior-modes.mdc", []),
            
            # Reasoning Framework
            (r"## L9 Multi-Modal Reasoning", "behavior", "reasoning-framework.mdc", [
                "MUST apply reasoning modes based on complexity",
                "MUST provide confidence scores",
                "MUST follow reasoning execution protocol"
            ]),
            
            # Workflows
            (r"## Preflight Checklist", "workflows", "pre-execution-checklist.mdc", [
                "MUST verify schema before n8n operations",
                "MUST confirm auth method",
                "MUST read credentials from .env",
                "MUST search existing solutions first"
            ]),
            (r"## Session Initialization", "workflows", "session-initialization.mdc", [
                "MUST load core governance files",
                "MUST load task-specific profiles",
                "MUST post verification confirmation"
            ]),
            (r"## Memory & Learning", "workflows", "learning-system.mdc", [
                "MUST retain session memory",
                "MUST auto-apply corrections",
                "MUST log mistakes immediately"
            ]),
            (r"## Recursive Learning Protocol", "workflows", "recursive-learning.mdc", []),
            
            # Domains
            (r"## N8N Automation Development", "domains", "n8n-automation.mdc", [
                "MUST research nodes first (MANDATORY)",
                "MUST follow workflow governance",
                "MUST validate against schema",
                "MUST run recursive self-check"
            ]),
            
            # Enterprise
            (r"## Enterprise Deliverable Standards", "enterprise", "enterprise-deliverables.mdc", [
                "MUST meet all 5 production-ready criteria",
                "MUST follow 3-phase deliverable process",
                "MUST complete quality control checklist"
            ]),
            
            # Protocols
            (r"## YNP Protocol", "behavior", "ynp-protocol.mdc", [
                "MUST conclude tasks with YNP",
                "MUST combine 3+ logical steps",
                "MUST reference specific deliverables"
            ]),
            (r"## Prompt Forge Meta Prompt", "workflows", "prompt-forge.mdc", [
                "MUST follow 7-step structure",
                "MUST provide copy/paste-ready commands",
                "MUST include troubleshooting section"
            ]),
            
            # Anti-Preferences
            (r"## Anti-Preferences", "behavior", "anti-preferences.mdc", [
                "MUST NOT use hedging language",
                "MUST NOT apologize or over-explain",
                "MUST NOT create duplicate files",
                "MUST NOT auto-generate READMEs"
            ]),
            
            # Verification
            (r"## Mandatory Response Format", "workflows", "verification-protocol.mdc", [
                "MUST post self-verification block",
                "MUST show evidence before claiming done",
                "MUST answer verification questions"
            ]),
            (r"## AI Self-Verification Protocol", "workflows", "self-verification.mdc", [
                "MUST complete pre-action self-audit",
                "MUST answer verification questions",
                "MUST show proof for each checkpoint"
            ]),
            
            # Commands
            (r"## High-Velocity Commands", "workflows", "slash-commands.mdc", []),
            
            # Documentation
            (r"## Documentation Structure", "core", "documentation-standards.mdc", [
                "MUST follow content order",
                "MUST use numbered BLOCKS",
                "MUST prefer ASCII diagrams"
            ]),
            
            # Search
            (r"## Search-First Principle", "workflows", "search-first.mdc", [
                "MUST search existing codebase first",
                "MUST check scripts/ directory",
                "MUST confirm before creating new"
            ]),
        ]
    
    def read_template(self) -> str:
        """Read the .cursorrules template file"""
        if not self.template_file.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_file}")
        
        with open(self.template_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def parse_sections(self, content: str) -> List[RuleSection]:
        """Parse content into rule sections"""
        sections = []
        
        # Split by major headers (##) - but keep section content together
        pattern = r'^(##+)\s+(.+)$'
        lines = content.split('\n')
        current_section = None
        current_content = []
        in_code_block = False
        
        for i, line in enumerate(lines):
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
            
            match = re.match(pattern, line)
            if match and not in_code_block:
                # Save previous section
                if current_section and current_content:
                    sections.append(RuleSection(
                        title=current_section,
                        content='\n'.join(current_content).strip(),
                        category="",
                        filename="",
                        enforceability_score=0,
                        dependencies=[]
                    ))
                
                # Start new section
                current_section = match.group(2)
                current_content = [line]
            else:
                if current_section:
                    current_content.append(line)
        
        # Add last section
        if current_section and current_content:
            sections.append(RuleSection(
                title=current_section,
                content='\n'.join(current_content).strip(),
                category="",
                filename="",
                enforceability_score=0,
                dependencies=[]
            ))
        
        return sections
    
    def enhance_enforceability(self, content: str, enhancements: List[str]) -> str:
        """Enhance content with enforceable language"""
        lines = content.split('\n')
        enhanced_lines = []
        
        for line in lines:
            # Convert suggestions to mandates
            if line.strip().startswith('-') and not any(word in line for word in ['MUST', 'MUST NOT', 'REQUIRED', 'MANDATORY']):
                # Check if it's a rule (not an example)
                if ':' in line and not line.strip().startswith('```'):
                    # Convert to MUST format
                    if line.strip().startswith('- **'):
                        # Keep bold formatting, add MUST
                        enhanced = line.replace('- **', '- **MUST: **', 1)
                        enhanced_lines.append(enhanced)
                    else:
                        enhanced = line.replace('- ', '- **MUST**: ', 1)
                        enhanced_lines.append(enhanced)
                else:
                    enhanced_lines.append(line)
            else:
                enhanced_lines.append(line)
        
        # Add enforcement checklist if enhancements provided
        if enhancements:
            enhanced_lines.append('\n## Enforcement Checklist')
            enhanced_lines.append('\n**Before proceeding, verify:**')
            for enhancement in enhancements:
                enhanced_lines.append(f'- [ ] {enhancement}')
        
        return '\n'.join(enhanced_lines)
    
    def create_rule_file(self, section: RuleSection, category: str, filename: str, 
                        enforceability_enhancements: List[str]) -> str:
        """Create a Project Rules .mdc file"""
        
        # Enhance content
        enhanced_content = self.enhance_content(section.content, enforceability_enhancements)
        
        # Build file content
        file_content = f"""# {section.title}

## Purpose
{self._extract_purpose(section.content)}

## Rules

{enhanced_content}

## Enforcement

**This rule is MANDATORY and automatically enforced by Cursor AI.**

### Verification
- Cursor AI checks compliance before code generation
- Violations trigger warnings and require correction
- All actions must pass pre-execution checklist

### Related Rules
{self._generate_related_rules(section.title)}

---
**Source**: Migrated from `.cursorrules` template
**Enforcement Level**: MANDATORY
**Last Updated**: 2025-11-20
"""
        
        return file_content
    
    def enhance_content(self, content: str, enhancements: List[str]) -> str:
        """Enhance content with enforceable language"""
        lines = content.split('\n')
        enhanced = []
        
        for line in lines:
            # Skip header lines
            if line.strip().startswith('#') or line.strip().startswith('---'):
                continue
            
            # Convert bullet points to MUST format
            if line.strip().startswith('-') and ':' in line:
                if '**' in line:
                    # Already has formatting
                    if 'MUST' not in line.upper() and 'MANDATORY' not in line.upper():
                        # Add MUST if not present
                        line = line.replace('- **', '- **MUST: **', 1)
                else:
                    # Plain bullet, add MUST
                    line = line.replace('- ', '- **MUST**: ', 1)
            
            enhanced.append(line)
        
        # Add enforcement checklist
        if enhancements:
            enhanced.append('\n### Pre-Execution Checklist')
            enhanced.append('\n**Before proceeding, verify:**')
            for enhancement in enhancements:
                enhanced.append(f'- [ ] {enhancement}')
        
        return '\n'.join(enhanced)
    
    def _extract_purpose(self, content: str) -> str:
        """Extract purpose from content"""
        # Look for purpose indicators
        purpose_patterns = [
            r'Purpose[:\s]+(.+?)(?:\n|$)',
            r'This rule (.+?)(?:\n|$)',
            r'Governs (.+?)(?:\n|$)',
        ]
        
        for pattern in purpose_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Default purpose
        return "Defines mandatory rules and standards for this domain."
    
    def _generate_related_rules(self, title: str) -> str:
        """Generate related rules references"""
        related = []
        
        # Map relationships
        relationships = {
            "Core Governance": ["@file-standards.mdc", "@development-workflow.mdc"],
            "File Standards": ["@governance-core.mdc", "@code-standards.mdc"],
            "Code & Technical Standards": ["@file-standards.mdc", "@pre-execution-checklist.mdc"],
            "Preflight Checklist": ["@n8n-automation.mdc", "@verification-protocol.mdc"],
            "N8N Automation": ["@pre-execution-checklist.mdc", "@search-first.mdc"],
        }
        
        for key, refs in relationships.items():
            if key.lower() in title.lower():
                return '\n'.join(f'- {ref}' for ref in refs)
        
        return '- See @index.mdc for all rules'
    
    def create_index_file(self, rules: List[Tuple[str, str, str]]) -> str:
        """Create index.mdc file"""
        content = """# Suite 6 Project Rules Index

## Overview
This directory contains all Project Rules migrated from `.cursorrules` template.
Each rule is enforceable and mandatory.

## Rule Categories

"""
        
        categories = {}
        for category, filename, title in rules:
            if category not in categories:
                categories[category] = []
            categories[category].append((filename, title))
        
        for category, files in sorted(categories.items()):
            content += f"### {category.title()}\n\n"
            for filename, title in files:
                content += f"- **{title}**: @{filename}\n"
            content += "\n"
        
        content += """## Enforcement

All rules in this directory are **MANDATORY** and automatically enforced by Cursor AI.

### How Rules Are Applied

1. **Automatic Loading**: Cursor loads all `.mdc` files from `.cursor/rules/` at project open
2. **Pre-Execution Checks**: Rules are checked before any code generation or file modification
3. **Violation Detection**: Non-compliance triggers warnings and requires correction
4. **Continuous Enforcement**: Rules apply throughout the entire session

### Rule Priority

- **MANDATORY** rules (marked with MUST/MUST NOT) are non-negotiable
- **RECOMMENDED** rules (marked with SHOULD) are best practices
- **OPTIONAL** rules (marked with MAY) are suggestions

## Migration Notes

- Migrated from: `.cursor-commands/templates/.cursorrules`
- Migration date: 2025-11-20
- Format: Cursor Project Rules (.mdc)
- Status: ✅ Active and enforced

---
**Last Updated**: 2025-11-20
"""
        
        return content
    
    def migrate(self):
        """Execute migration"""
        print("🚀 Starting Project Rules Migration...")
        print(f"📁 Workspace: {self.workspace}")
        print(f"📄 Template: {self.template_file}")
        print(f"📂 Target: {self.cursor_rules_dir}\n")
        
        # Create directory structure
        categories = ["core", "behavior", "workflows", "domains", "enterprise"]
        for category in categories:
            (self.cursor_rules_dir / category).mkdir(parents=True, exist_ok=True)
        
        # Read template
        print("📖 Reading template file...")
        content = self.read_template()
        
        # Parse sections
        print("🔍 Parsing sections...")
        sections = self.parse_sections(content)
        print(f"   Found {len(sections)} sections\n")
        
        # Create rule files
        created_rules = []
        
        for section in sections:
            # Find matching rule mapping
            matched = False
            for pattern, category, filename, enhancements in self.rule_mappings:
                if re.search(pattern, section.title, re.IGNORECASE):
                    matched = True
                    
                    # Create file
                    file_path = self.cursor_rules_dir / category / filename
                    rule_content = self.create_rule_file(
                        section, category, filename, enhancements
                    )
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(rule_content)
                    
                    created_rules.append((category, filename, section.title))
                    print(f"✅ Created: {category}/{filename}")
                    break
            
            if not matched:
                # Create generic file for unmatched sections
                safe_name = re.sub(r'[^\w\s-]', '', section.title).strip().replace(' ', '-').lower()
                filename = f"{safe_name}.mdc"
                file_path = self.cursor_rules_dir / "core" / filename
                
                rule_content = f"""# {section.title}

## Purpose
Rules and guidelines for {section.title.lower()}.

## Rules

{section.content}

## Enforcement

**This rule is MANDATORY and automatically enforced by Cursor AI.**

---
**Source**: Migrated from `.cursorrules` template
**Last Updated**: 2025-11-20
"""
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(rule_content)
                
                created_rules.append(("core", filename, section.title))
                print(f"⚠️  Created generic: core/{filename}")
        
        # Create index file
        print("\n📑 Creating index file...")
        index_content = self.create_index_file(created_rules)
        index_path = self.cursor_rules_dir / "index.mdc"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        print(f"✅ Created: index.mdc")
        
        # Summary
        print(f"\n{'='*60}")
        print("✅ Migration Complete!")
        print(f"{'='*60}")
        print(f"\n📊 Summary:")
        print(f"   Rules created: {len(created_rules)}")
        print(f"   Categories: {len(set(cat for cat, _, _ in created_rules))}")
        print(f"\n📂 Structure:")
        for category in categories:
            count = sum(1 for cat, _, _ in created_rules if cat == category)
            print(f"   {category}/: {count} files")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Review generated files in: {self.cursor_rules_dir}")
        print(f"   2. Test rules are loading correctly")
        print(f"   3. Update .cursorrules to point to Project Rules")
        print(f"   4. Remove deprecated .cursorrules after validation")

if __name__ == '__main__':
    migrator = ProjectRulesMigrator()
    migrator.migrate()

