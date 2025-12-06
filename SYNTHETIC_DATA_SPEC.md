# Synthetic Data Specification

## Overview
This document defines the synthetic data model for the IEEE paper simulation. The goal is to generate realistic, diverse employee profiles and their behavioral metadata across multiple enterprise systems.

---

## Job Roles & Tech Stacks

| Role | Department | Primary Stack | Cloud | Common Risk Patterns |
|------|------------|---------------|-------|---------------------|
| **Developer (Backend)** | Engineering | Python, Java, Go | AWS | Secrets in code, PRs without review |
| **Developer (Frontend)** | Engineering | JavaScript, React, TypeScript | AWS | Vulnerable npm packages, XSS issues |
| **DevOps Engineer** | Platform | Terraform, Kubernetes, Docker | AWS + GCP | Open security groups, privileged IAM |
| **DevSecOps Engineer** | Security | Python, AWS, GCP, Splunk | AWS + GCP | Actually low risk - they fix issues |
| **Cloud Security Analyst** | Security | AWS, GCP, Sentinel, CrowdStrike | AWS + GCP | Low risk - monitors others |
| **Data Analyst** | Data Platform | SQL, Python, BigQuery | GCP | Data exfil via BigQuery, large exports |
| **Data Engineer** | Data Platform | Python, Spark, Airflow, BigQuery | GCP | Service account key creation, IAM escalation |
| **SRE** | Reliability | Go, Kubernetes, Terraform | AWS + GCP | Emergency prod access, break-glass usage |

---

## Cloud Services Per Role

### AWS Services
| Service | Roles That Use It | Risk Events |
|---------|-------------------|-------------|
| **IAM** | All | AssumeRole, CreateAccessKey, AttachUserPolicy |
| **S3** | DevOps, Data Eng, SRE | Public bucket, large downloads |
| **EC2** | Backend Dev, DevOps | Open security groups, unencrypted EBS |
| **RDS** | Backend Dev | Public snapshots, weak passwords |
| **Lambda** | Backend Dev, DevOps | Overpermissioned roles |
| **EKS** | DevOps, SRE | Privileged pods, exposed API server |
| **CloudTrail** | Security, DevSecOps | Log tampering (if malicious) |

### GCP Services
| Service | Roles That Use It | Risk Events |
|---------|-------------------|-------------|
| **IAM** | All | SetIamPolicy, CreateServiceAccountKey |
| **BigQuery** | Data Analyst, Data Eng | Large exports, external sharing |
| **GCS** | Data Eng, DevOps | Public buckets, allUsers access |
| **GKE** | DevOps, SRE | Privileged pods, Workload Identity bypass |
| **Cloud Functions** | Backend Dev | Overpermissioned service accounts |
| **Compute Engine** | All | SSH key modifications, firewall changes |
| **Cloud Logging** | Security | Log deletion (if malicious) |

---

## Risk Scenarios Per Role

### Developer (Backend) - High Git Risk
```
- Commits secrets (API keys, passwords) to repo
- Force pushes to main/master
- Skips PR reviews for urgent hotfixes
- Large binary file additions
```

### Developer (Frontend) - Medium Git + Medium Vulnerability Risk
```
- Uses vulnerable npm packages
- Commits .env files
- XSS/CSRF vulnerabilities in code reviews
- Third-party script inclusions
```

### DevOps Engineer - High IAM Risk
```
- Creates overpermissioned Terraform roles
- Opens 0.0.0.0/0 security groups
- Uses admin credentials in CI/CD
- Terraform state stored insecurely
```

### DevSecOps Engineer - Low Risk (Control Group)
```
- Closes security tickets quickly
- No secrets in code
- Proper least-privilege IAM
- Regular training completion
```

### Cloud Security Analyst - Very Low Risk (Control Group)
```
- Monitor-only access
- High training completion
- No code commits
- Review-only Jira tickets
```

### Data Analyst - Medium Data Exfil Risk
```
- Large BigQuery exports
- External sharing of datasets
- Query patterns on sensitive tables
- Long-running resource-intensive queries
```

### Data Engineer - High IAM + Data Risk
```
- Service account key creation
- Airflow DAG with hardcoded creds
- BigQuery owner permissions
- Cross-project data movement
```

### SRE - Situational High Risk
```
- Break-glass access usage
- Emergency prod access
- Privilege escalation during incidents
- Post-incident access not revoked
```

---

## Distribution for 50 Users

| Role | Count | Expected Risk Level |
|------|-------|---------------------|
| Developer (Backend) | 12 | High (0.6-0.9) |
| Developer (Frontend) | 8 | Medium (0.4-0.6) |
| DevOps Engineer | 8 | High (0.6-0.8) |
| DevSecOps Engineer | 4 | Low (0.1-0.3) |
| Cloud Security Analyst | 3 | Very Low (0.0-0.2) |
| Data Analyst | 6 | Medium (0.3-0.5) |
| Data Engineer | 6 | High (0.5-0.8) |
| SRE | 3 | Variable (0.2-0.9) |
| **Total** | **50** | |

---

## Event Generation (30 Days)

### Per-User Event Counts
| Event Type | Low Risk User | Medium Risk User | High Risk User |
|------------|---------------|------------------|----------------|
| Git Commits | 50-100 | 50-100 | 50-100 |
| Secrets Detected | 0 | 1-2 | 3-5 |
| Force Pushes | 0 | 1 | 2-5 |
| Jira Tickets | 5-10 | 10-20 | 15-30 |
| Overdue Tickets | 0 | 1-3 | 5-10 |
| IAM Events | 10-20 | 20-50 | 50-100 |
| Privileged Actions | 0-2 | 5-10 | 15-30 |
| SIEM Alerts | 0 | 1-2 | 3-10 |

---

## Training Recommendations Per Role

| Role | Recommended Modules |
|------|---------------------|
| Developer (Backend) | Secrets Management, Secure Coding |
| Developer (Frontend) | XSS Prevention, Dependency Security |
| DevOps Engineer | IAM Best Practices, IaC Security |
| Data Analyst | Data Classification, BigQuery Security |
| Data Engineer | Service Account Security, Data Pipeline Security |
| SRE | Incident Response Security, Privilege Management |

---

## Next Steps
1. [ ] Update `historical_data_generator.py` with these roles
2. [ ] Add cloud-specific event generation
3. [ ] Implement role-based risk weighting
4. [ ] Test with 50 users and verify risk distribution
