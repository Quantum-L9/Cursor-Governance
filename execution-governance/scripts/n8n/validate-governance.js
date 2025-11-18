#!/usr/bin/env node
/**
 * Suite 6 Governance Validation Script (JavaScript/Node.js)
 * 
 * Cross-platform governance validation tool based on Constellation's
 * validate-stub.js with Suite 6 enhancements.
 * 
 * Usage: node validate-governance.js [options]
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class Suite6GovernanceValidator {
    constructor() {
        this.suiteRoot = process.cwd();
        this.results = {
            totalFiles: 0,
            validFiles: 0,
            invalidFiles: 0,
            errors: [],
            warnings: []
        };
    }

    /**
     * Validate Suite 6 canonical headers in markdown files
     */
    validateCanonicalHeaders(filePath) {
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            
            if (!content.startsWith('---')) {
                return {
                    valid: false,
                    error: 'Missing YAML frontmatter'
                };
            }

            const headerEnd = content.indexOf('---', 3);
            if (headerEnd === -1) {
                return {
                    valid: false,
                    error: 'Incomplete YAML frontmatter'
                };
            }

            const headerContent = content.substring(3, headerEnd).trim();
            
            // Check for Suite 6 canonical header marker
            if (!headerContent.includes('=== SUITE 6 CANONICAL HEADER ===')) {
                return {
                    valid: false,
                    error: 'Missing Suite 6 canonical header marker'
                };
            }

            // Check required fields
            const requiredFields = [
                'suite:', 'version:', 'component_id:', 'component_name:',
                'layer:', 'domain:', 'type:', 'status:', 'created:', 'updated:',
                'author:', 'maintainer:', 'governance_level:', 'purpose:'
            ];

            const missingFields = [];
            for (const field of requiredFields) {
                if (!headerContent.includes(field)) {
                    missingFields.push(field.replace(':', ''));
                }
            }

            if (missingFields.length > 0) {
                return {
                    valid: false,
                    error: `Missing required fields: ${missingFields.join(', ')}`
                };
            }

            // Validate component ID format
            const componentIdMatch = headerContent.match(/component_id:\s*["\']?([^"\'\n]+)["\']?/);
            if (componentIdMatch) {
                const componentId = componentIdMatch[1].trim();
                if (!/^[A-Z]{3}-[A-Z]{2,3}-\d{3}$/.test(componentId)) {
                    return {
                        valid: false,
                        error: `Invalid component ID format: ${componentId}. Expected format: XXX-XX-###`
                    };
                }
            }

            return { valid: true };

        } catch (error) {
            return {
                valid: false,
                error: `Error reading file: ${error.message}`
            };
        }
    }

    /**
     * Validate agent stub JSON files
     */
    validateAgentStub(filePath) {
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            const stub = JSON.parse(content);

            const requiredFields = [
                'agent', 'component_id', 'agent_version', 'governance_kernel',
                'rules_enforced', 'snapshot_required', 'override_enabled',
                'linter_verified', 'last_validated'
            ];

            const missingFields = [];
            for (const field of requiredFields) {
                if (!(field in stub)) {
                    missingFields.push(field);
                }
            }

            if (missingFields.length > 0) {
                return {
                    valid: false,
                    error: `Missing required fields: ${missingFields.join(', ')}`
                };
            }

            // Validate governance kernel version
            if (stub.governance_kernel !== '6.0') {
                return {
                    valid: false,
                    error: `Invalid governance kernel version: ${stub.governance_kernel}. Expected: 6.0`
                };
            }

            // Validate component ID format
            if (!/^[A-Z]{3}-[A-Z]{2,3}-\d{3}$/.test(stub.component_id)) {
                return {
                    valid: false,
                    error: `Invalid component ID format: ${stub.component_id}`
                };
            }

            // Validate date format
            const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
            if (!dateRegex.test(stub.last_validated)) {
                return {
                    valid: false,
                    error: `Invalid date format for last_validated: ${stub.last_validated}`
                };
            }

            // Check if validation is stale (>30 days)
            const lastValidated = new Date(stub.last_validated);
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

            if (lastValidated < thirtyDaysAgo) {
                return {
                    valid: true,
                    warning: `Validation is stale (${Math.floor((Date.now() - lastValidated.getTime()) / (1000 * 60 * 60 * 24))} days old)`
                };
            }

            return { valid: true };

        } catch (error) {
            return {
                valid: false,
                error: `Error parsing JSON: ${error.message}`
            };
        }
    }

    /**
     * Generate SHA256 hash for file integrity checking
     */
    generateFileHash(filePath) {
        try {
            const content = fs.readFileSync(filePath);
            const hash = crypto.createHash('sha256').update(content).digest('hex');
            return hash;
        } catch (error) {
            return null;
        }
    }

    /**
     * Verify file integrity against stored signatures
     */
    verifyFileIntegrity(filePath) {
        const fileName = path.basename(filePath);
        const signaturesDir = path.join(this.suiteRoot, 'foundation', 'security', 'signatures');
        const signatureFile = path.join(signaturesDir, `${fileName}.sig.json`);

        if (!fs.existsSync(signatureFile)) {
            return {
                valid: false,
                error: 'No signature file found'
            };
        }

        try {
            const signature = JSON.parse(fs.readFileSync(signatureFile, 'utf8'));
            const currentHash = this.generateFileHash(filePath);

            if (!currentHash) {
                return {
                    valid: false,
                    error: 'Could not generate file hash'
                };
            }

            if (signature.hash !== currentHash) {
                return {
                    valid: false,
                    error: 'File integrity violation - hash mismatch'
                };
            }

            return {
                valid: true,
                signedBy: signature.signed_by,
                signedOn: signature.signed_on
            };

        } catch (error) {
            return {
                valid: false,
                error: `Error verifying signature: ${error.message}`
            };
        }
    }

    /**
     * Scan directory for governance files
     */
    scanGovernanceFiles(directory) {
        const files = [];
        
        try {
            const entries = fs.readdirSync(directory, { withFileTypes: true });
            
            for (const entry of entries) {
                const fullPath = path.join(directory, entry.name);
                
                if (entry.isDirectory() && !entry.name.startsWith('.')) {
                    files.push(...this.scanGovernanceFiles(fullPath));
                } else if (entry.isFile()) {
                    const ext = path.extname(entry.name).toLowerCase();
                    // Skip signature files and other non-governance files
                    if (entry.name.includes('.sig.json') || 
                        entry.name.includes('debug-') || 
                        entry.name.includes('test-') ||
                        entry.name.includes('.log')) {
                        continue;
                    }
                    if (ext === '.md' || ext === '.json') {
                        files.push(fullPath);
                    }
                }
            }
        } catch (error) {
            console.error(`Error scanning directory ${directory}: ${error.message}`);
        }

        return files;
    }

    /**
     * Validate all governance files
     */
    validateAll() {
        console.log('🔍 Starting Suite 6 governance validation...\n');

        const governanceDirs = [
            'intelligence',
            'foundation', 
            'execution',
            'operations',
            'environment'
        ];

        for (const dir of governanceDirs) {
            const dirPath = path.join(this.suiteRoot, dir);
            if (!fs.existsSync(dirPath)) {
                console.log(`⚠️  Directory not found: ${dir}`);
                continue;
            }

            console.log(`📁 Scanning ${dir}/`);
            const files = this.scanGovernanceFiles(dirPath);

            for (const filePath of files) {
                this.validateFile(filePath);
            }
        }

        this.printResults();
    }

    /**
     * Validate individual file
     */
    validateFile(filePath) {
        this.results.totalFiles++;
        const relativePath = path.relative(this.suiteRoot, filePath);
        const ext = path.extname(filePath).toLowerCase();

        let result;
        
        if (ext === '.md') {
            result = this.validateCanonicalHeaders(filePath);
        } else if (ext === '.json' && filePath.includes('stub.json')) {
            result = this.validateAgentStub(filePath);
        } else {
            // Skip non-governance files
            this.results.totalFiles--;
            return;
        }

        if (result.valid) {
            this.results.validFiles++;
            console.log(`✅ ${relativePath}`);
            
            if (result.warning) {
                this.results.warnings.push(`${relativePath}: ${result.warning}`);
                console.log(`   ⚠️  ${result.warning}`);
            }

            // Check file integrity if signature exists
            const integrityResult = this.verifyFileIntegrity(filePath);
            if (integrityResult.valid) {
                console.log(`   🔐 Integrity verified (signed by ${integrityResult.signedBy})`);
            } else if (integrityResult.error !== 'No signature file found') {
                console.log(`   ❌ ${integrityResult.error}`);
            }

        } else {
            this.results.invalidFiles++;
            this.results.errors.push(`${relativePath}: ${result.error}`);
            console.log(`❌ ${relativePath}`);
            console.log(`   Error: ${result.error}`);
        }
    }

    /**
     * Print validation results summary
     */
    printResults() {
        console.log('\n' + '='.repeat(60));
        console.log('📊 SUITE 6 GOVERNANCE VALIDATION RESULTS');
        console.log('='.repeat(60));
        
        console.log(`Total files processed: ${this.results.totalFiles}`);
        console.log(`Valid files: ${this.results.validFiles} ✅`);
        console.log(`Invalid files: ${this.results.invalidFiles} ❌`);
        console.log(`Warnings: ${this.results.warnings.length} ⚠️`);

        const complianceRate = this.results.totalFiles > 0 
            ? ((this.results.validFiles / this.results.totalFiles) * 100).toFixed(1)
            : 0;
        
        console.log(`Compliance rate: ${complianceRate}%`);

        if (this.results.warnings.length > 0) {
            console.log('\n⚠️  WARNINGS:');
            this.results.warnings.forEach(warning => console.log(`   ${warning}`));
        }

        if (this.results.errors.length > 0) {
            console.log('\n❌ ERRORS:');
            this.results.errors.forEach(error => console.log(`   ${error}`));
        }

        console.log('\n' + '='.repeat(60));

        // Exit with error code if validation failed
        if (this.results.invalidFiles > 0) {
            process.exit(1);
        }
    }

    /**
     * Generate governance health report
     */
    generateHealthReport() {
        const report = {
            timestamp: new Date().toISOString(),
            suite_version: '6.0.0',
            validation_results: this.results,
            compliance_rate: this.results.totalFiles > 0 
                ? ((this.results.validFiles / this.results.totalFiles) * 100)
                : 0,
            recommendations: []
        };

        // Add recommendations based on results
        if (this.results.invalidFiles > 0) {
            report.recommendations.push('Fix governance violations before deployment');
        }
        
        if (this.results.warnings.length > 0) {
            report.recommendations.push('Address validation warnings to improve compliance');
        }

        if (report.compliance_rate < 95) {
            report.recommendations.push('Improve governance compliance to meet 95% target');
        }

        // Save report
        const reportPath = path.join(this.suiteRoot, 'governance-health-report.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        
        console.log(`📄 Health report saved to: ${reportPath}`);
        return report;
    }
}

// CLI interface
function main() {
    const args = process.argv.slice(2);
    const validator = new Suite6GovernanceValidator();

    if (args.includes('--help') || args.includes('-h')) {
        console.log(`
Suite 6 Governance Validator (JavaScript)

Usage: node validate-governance.js [options]

Options:
  --help, -h          Show this help message
  --file <path>       Validate specific file
  --report            Generate health report
  --version           Show version information

Examples:
  node validate-governance.js                           # Validate all governance files
  node validate-governance.js --file foundation/logic/universal-kernel.md
  node validate-governance.js --report                  # Generate health report
        `);
        return;
    }

    if (args.includes('--version')) {
        console.log('Suite 6 Governance Validator v6.0.0');
        return;
    }

    const fileIndex = args.indexOf('--file');
    if (fileIndex !== -1 && args[fileIndex + 1]) {
        const filePath = args[fileIndex + 1];
        if (fs.existsSync(filePath)) {
            validator.validateFile(filePath);
            validator.printResults();
        } else {
            console.error(`❌ File not found: ${filePath}`);
            process.exit(1);
        }
        return;
    }

    // Default: validate all files
    validator.validateAll();

    if (args.includes('--report')) {
        validator.generateHealthReport();
    }
}

if (require.main === module) {
    main();
}

module.exports = Suite6GovernanceValidator;
