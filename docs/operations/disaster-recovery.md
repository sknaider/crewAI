# CrewAI Disaster Recovery Plan (DRP)

**Version:** 1.0
**Last Updated:** 2025-11-16
**Owner:** Platform Engineering Team
**Contact:** support@crewai.com

---

## Table of Contents

1. [Overview](#overview)
2. [Recovery Objectives](#recovery-objectives)
3. [Incident Response Team](#incident-response-team)
4. [Backup Strategy](#backup-strategy)
5. [Recovery Procedures](#recovery-procedures)
6. [Runbooks](#runbooks)
7. [Testing and Validation](#testing-and-validation)
8. [Communication Plan](#communication-plan)

---

## Overview

This Disaster Recovery Plan outlines procedures for recovering the CrewAI platform from various failure scenarios including:

- Complete data center outage
- Database corruption/failure
- Security breach
- Application failure
- Infrastructure compromise

**Scope:** Production CrewAI environment in AWS us-east-1 with DR site in us-west-2

---

## Recovery Objectives

### Recovery Time Objective (RTO)

| Service Component | RTO | Priority |
|-------------------|-----|----------|
| **Core API** | 1 hour | P0 - Critical |
| **Database** | 1 hour | P0 - Critical |
| **LLM Integration** | 30 minutes | P0 - Critical |
| **Memory Storage** | 2 hours | P1 - High |
| **Telemetry** | 4 hours | P2 - Medium |
| **Documentation** | 24 hours | P3 - Low |

### Recovery Point Objective (RPO)

| Data Type | RPO | Backup Frequency |
|-----------|-----|------------------|
| **Database** | 15 minutes | Continuous replication + 15min snapshots |
| **File Storage (S3)** | 1 hour | Hourly sync to DR region |
| **Configuration** | 0 minutes | Versioned in Git |
| **Logs** | 5 minutes | Real-time streaming to CloudWatch |

---

## Incident Response Team

### Core Team

| Role | Primary | Backup | Contact |
|------|---------|--------|---------|
| **Incident Commander** | John Doe | Jane Smith | +1-555-0100 |
| **Platform Engineer** | Alice Brown | Bob White | +1-555-0101 |
| **Database Admin** | Charlie Green | David Black | +1-555-0102 |
| **Security Lead** | Eve Red | Frank Blue | +1-555-0103 |
| **Communications** | Grace Yellow | Harry Orange | +1-555-0104 |

### Escalation Path

1. **P0/P1 Incidents:** Immediate notification to Incident Commander
2. **P2 Incidents:** Notify on-call engineer
3. **P3 Incidents:** Create ticket, address during business hours

**On-Call Rotation:** PagerDuty schedule `crewai-oncall-primary`

---

## Backup Strategy

### Automated Backups

#### Database (PostgreSQL/RDS)

```bash
# Automated RDS snapshots
- Frequency: Every 15 minutes
- Retention: 7 days
- Cross-region replication: us-west-2
- Encryption: AWS KMS

# Point-in-time recovery
- Window: Up to 7 days
- Granularity: 5-minute intervals
```

#### File Storage (S3/EFS)

```bash
# S3 Cross-Region Replication
aws s3 sync s3://crewai-prod-us-east-1 s3://crewai-dr-us-west-2 \
  --delete --storage-class STANDARD_IA

# EFS Backups
- AWS Backup schedule: Daily at 03:00 UTC
- Retention: 30 days
- Recovery: Restore to new EFS or in-place
```

#### Configuration and Secrets

```bash
# Git-based configuration (Infrastructure as Code)
- Repository: github.com/crewai/infrastructure
- Branch protection: main branch requires review
- Automated sync: ArgoCD

# AWS Secrets Manager
- Automatic rotation: 30 days
- Cross-region replication: Enabled
- Version retention: 10 versions
```

### Backup Verification

**Monthly Verification:**
```bash
# Automated backup restore test
./scripts/test-backup-restore.sh --env=staging --date=latest

# Steps:
# 1. Restore DB snapshot to staging
# 2. Validate data integrity
# 3. Run smoke tests
# 4. Document results
```

---

## Recovery Procedures

### Scenario 1: Complete Regional Outage (AWS us-east-1)

**Detection:**
- CloudWatch alarms: `RegionalHealthCheck` triggered
- Multiple availability zones unreachable
- API health checks failing across all AZs

**Recovery Steps:**

1. **Declare Disaster (0-5 minutes)**
   ```bash
   # Incident Commander declares DR
   python scripts/declare-disaster.py \
     --region=us-east-1 \
     --severity=P0 \
     --type=regional-outage
   ```

2. **Failover to DR Site (5-30 minutes)**
   ```bash
   # Execute automated failover
   ./scripts/failover-to-dr.sh \
     --source-region=us-east-1 \
     --target-region=us-west-2 \
     --confirm

   # Steps performed:
   # - Update Route53 to point to DR region
   # - Promote read replica to primary database
   # - Scale up EKS cluster in us-west-2
   # - Update secrets and configuration
   # - Run smoke tests
   ```

3. **Verify Services (30-45 minutes)**
   ```bash
   # Run comprehensive health checks
   python scripts/verify-dr-readiness.py \
     --region=us-west-2 \
     --full-suite

   # Check:
   # ✓ API endpoints responding
   # ✓ Database connectivity
   # ✓ LLM provider access
   # ✓ Memory storage accessible
   # ✓ Metrics collection working
   ```

4. **Enable Traffic (45-60 minutes)**
   ```bash
   # Gradually shift traffic to DR
   ./scripts/shift-traffic.sh \
     --target=us-west-2 \
     --strategy=gradual \
     --duration=15m

   # Monitor:
   # - Error rates
   # - Latency (p50, p95, p99)
   # - Success rates
   ```

**Rollback Procedure:**
```bash
# If DR failover has issues
./scripts/rollback-failover.sh --reason="<description>"
```

---

### Scenario 2: Database Corruption/Failure

**Detection:**
- Database connection failures
- Data integrity check failures
- Application throwing database errors

**Recovery Steps:**

1. **Assess Damage (0-10 minutes)**
   ```bash
   # Check database status
   aws rds describe-db-instances \
     --db-instance-identifier crewai-prod-db

   # Check recent backups
   aws rds describe-db-snapshots \
     --db-instance-identifier crewai-prod-db \
     --max-items 10
   ```

2. **Stop Write Operations (10-15 minutes)**
   ```bash
   # Scale down application to read-only mode
   kubectl scale deployment crewai-service \
     --replicas=0 \
     --namespace=crewai

   # Or use feature flag
   python scripts/enable-feature-flag.py \
     --flag=maintenance_mode \
     --enabled=true
   ```

3. **Restore from Backup (15-45 minutes)**
   ```bash
   # Restore from latest snapshot
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier crewai-prod-db-restored \
     --db-snapshot-identifier crewai-prod-db-auto-snapshot-2025-11-16-03-00 \
     --db-instance-class db.r6g.2xlarge \
     --multi-az

   # Wait for restoration
   aws rds wait db-instance-available \
     --db-instance-identifier crewai-prod-db-restored
   ```

4. **Validate Data Integrity (45-55 minutes)**
   ```bash
   # Run data integrity checks
   python scripts/validate-database.py \
     --host=crewai-prod-db-restored.xxxxx.us-east-1.rds.amazonaws.com \
     --checks=all

   # Verify:
   # - Row counts match expected ranges
   # - No orphaned records
   # - Foreign key integrity
   # - Critical data present
   ```

5. **Update Application Configuration (55-60 minutes)**
   ```bash
   # Update database endpoint
   kubectl set env deployment/crewai-service \
     DATABASE_URL="postgresql://..." \
     --namespace=crewai

   # Scale up application
   kubectl scale deployment crewai-service \
     --replicas=3 \
     --namespace=crewai
   ```

**Expected Downtime:** 45-60 minutes

---

### Scenario 3: Security Breach / Compromise

**Detection:**
- Security alerts from AWS GuardDuty
- Unusual API access patterns
- Unauthorized data access attempts

**Immediate Actions (0-15 minutes):**

1. **Contain Breach**
   ```bash
   # Isolate affected systems
   ./scripts/security-lockdown.sh \
     --mode=full-isolation

   # Actions:
   # - Block all external traffic
   # - Disable API keys
   # - Revoke active sessions
   # - Enable enhanced logging
   ```

2. **Rotate All Credentials**
   ```bash
   # Emergency credential rotation
   ./scripts/rotate-all-secrets.sh \
     --emergency \
     --notify-team

   # Rotates:
   # - Database passwords
   # - API keys (LLM providers)
   # - JWT secrets
   # - AWS access keys
   # - Encryption keys
   ```

3. **Review Access Logs**
   ```bash
   # Export logs for forensic analysis
   aws logs create-export-task \
     --log-group-name /aws/crewai/production \
     --from $(date -d '24 hours ago' +%s)000 \
     --to $(date +%s)000 \
     --destination crewai-security-forensics

   # Run automated threat detection
   python scripts/analyze-security-incident.py \
     --timeframe=24h \
     --output=incident-report.json
   ```

4. **Notify Stakeholders**
   ```bash
   # Internal notification
   ./scripts/notify-security-incident.sh \
     --severity=critical \
     --channel=security-incidents

   # External notification (if customer data affected)
   # Follow legal/compliance procedures
   ```

**Recovery (15 minutes - 4 hours):**

- Patch vulnerabilities
- Restore from clean backup if needed
- Implement additional security controls
- Document incident for post-mortem

---

### Scenario 4: Application Failure / Crash Loop

**Detection:**
- Kubernetes pods in CrashLoopBackOff
- High error rates in logs
- Health checks failing

**Recovery Steps:**

1. **Check Pod Status (0-2 minutes)**
   ```bash
   kubectl get pods -n crewai
   kubectl describe pod <failing-pod> -n crewai
   kubectl logs <failing-pod> -n crewai --tail=100
   ```

2. **Attempt Quick Fixes (2-10 minutes)**
   ```bash
   # Restart deployment
   kubectl rollout restart deployment/crewai-service -n crewai

   # If that fails, rollback to previous version
   kubectl rollout undo deployment/crewai-service -n crewai

   # Check rollout status
   kubectl rollout status deployment/crewai-service -n crewai
   ```

3. **If Rollback Fails - Emergency Restore (10-30 minutes)**
   ```bash
   # Deploy known-good version
   kubectl set image deployment/crewai-service \
     crewai=crewai:1.4.9-stable \
     -n crewai

   # Or use Helm rollback
   helm rollback crewai -n crewai
   ```

**Expected Recovery Time:** 5-30 minutes

---

## Runbooks

### Quick Reference Commands

```bash
# Check system health
./scripts/health-check.sh --full

# View recent errors
kubectl logs -n crewai deployment/crewai-service \
  --tail=100 | grep ERROR

# Check database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h $DB_HOST -U $DB_USER -d crewai

# View metrics dashboard
open https://grafana.crewai.com/d/crewai-overview

# Check current traffic levels
kubectl top pods -n crewai

# Emergency scale-down
kubectl scale deployment/crewai-service --replicas=0 -n crewai

# Emergency scale-up
kubectl scale deployment/crewai-service --replicas=5 -n crewai
```

### Monitoring Dashboards

- **Grafana:** https://grafana.crewai.com
- **CloudWatch:** https://console.aws.amazon.com/cloudwatch
- **PagerDuty:** https://crewai.pagerduty.com
- **Status Page:** https://status.crewai.com

---

## Testing and Validation

### DR Drill Schedule

| Test Type | Frequency | Next Scheduled |
|-----------|-----------|----------------|
| **Backup Restore Test** | Monthly | 2025-12-01 |
| **Failover Drill** | Quarterly | 2026-01-15 |
| **Full DR Exercise** | Annually | 2026-06-01 |
| **Security Incident Simulation** | Semi-annually | 2026-03-01 |

### DR Drill Procedure

```bash
# 1. Schedule drill (2 weeks notice)
./scripts/schedule-dr-drill.sh \
  --date=2025-12-01 \
  --type=failover \
  --notify-stakeholders

# 2. Execute drill
./scripts/execute-dr-drill.sh \
  --type=failover \
  --target-region=us-west-2 \
  --dry-run=false

# 3. Document results
./scripts/generate-drill-report.sh \
  --drill-id=2025-12-01-failover \
  --output=reports/
```

### Success Criteria

- ✅ RTO met for all P0/P1 services
- ✅ RPO met (data loss within acceptable limits)
- ✅ All critical functions operational
- ✅ No data corruption
- ✅ Monitoring and alerting functional

---

## Communication Plan

### Internal Communication

**Slack Channels:**
- `#incidents-p0` - Critical incidents
- `#incidents-p1-p2` - High/medium priority
- `#crewai-status` - General status updates

**Email Distribution Lists:**
- `incidents@crewai.com` - All incidents
- `leadership@crewai.com` - P0/P1 only

### External Communication

**Status Page:** https://status.crewai.com
**Update Frequency:** Every 30 minutes during incident

**Customer Notification Templates:**

```markdown
Subject: [RESOLVED] CrewAI Service Disruption

Dear Valued Customer,

We experienced a service disruption affecting the CrewAI platform
from [START_TIME] to [END_TIME] UTC.

Impact: [DESCRIPTION]
Root Cause: [BRIEF_EXPLANATION]
Resolution: [ACTIONS_TAKEN]

We apologize for any inconvenience this may have caused.

Sincerely,
CrewAI Platform Team
```

---

## Appendix

### Contact Information

- **Emergency Hotline:** +1-555-CREWAI-HELP
- **Email:** emergency@crewai.com
- **PagerDuty:** https://crewai.pagerduty.com/incidents

### External Dependencies

| Service | SLA | Contact |
|---------|-----|---------|
| **AWS** | 99.99% | AWS Support Portal |
| **OpenAI** | 99.9% | platform.openai.com/support |
| **Datadog** | 99.9% | support@datadoghq.com |

### Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | Platform Team | Initial version |

---

**Last Reviewed:** 2025-11-16
**Next Review:** 2026-02-16
**Document Owner:** Platform Engineering Lead
