# Infrastructure Documentation

## Overview

Mission Control infrastructure supports both local development and cloud deployment with a focus on Google Cloud Platform.

## Local Development

### Requirements

- Docker Desktop
- Docker Compose v2.0+
- 4GB+ RAM available
- Ports: 3000, 5432, 6379, 8000

### Services

```yaml
Services:
  postgres    - PostgreSQL 16     - Port 5432
  redis       - Redis 7           - Port 6379
  backend     - FastAPI           - Port 8000
  frontend    - Next.js           - Port 3000
  migrate     - Alembic           - One-time
```

### Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Verify services
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Stop services
docker-compose down
```

## Production Infrastructure (GCP)

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Google Cloud Platform                │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────┐      ┌─────────────────┐      │
│  │   Cloud Load    │      │  Cloud CDN      │      │
│  │   Balancer      │      │                 │      │
│  └────────┬────────┘      └────────┬────────┘      │
│           │                         │                │
│  ┌────────▼────────┐      ┌────────▼────────┐      │
│  │  Cloud Run      │      │  Cloud Run      │      │
│  │  (Backend API)  │      │  (Frontend)     │      │
│  └────────┬────────┘      └─────────────────┘      │
│           │                                          │
│  ┌────────▼────────────────────┐                   │
│  │     Cloud SQL (PostgreSQL)   │                   │
│  └──────────────────────────────┘                   │
│           │                                          │
│  ┌────────▼────────────────────┐                   │
│  │   Memorystore (Redis)        │                   │
│  └──────────────────────────────┘                   │
│                                                       │
│  ┌──────────────────────────────┐                   │
│  │     Secret Manager           │                   │
│  └──────────────────────────────┘                   │
│                                                       │
└───────────────┬──────────────────────────────────────┘
                │
    ┌───────────▼────────────┐
    │   OpenClaw Gateway     │
    │   (On-Premise/GCE)     │
    └────────────────────────┘
```

### GCP Services Configuration

#### 1. Cloud Run (Backend)

```yaml
Service: mission-control-backend
Memory: 1Gi
CPU: 1
Min Instances: 1
Max Instances: 100
Concurrency: 1000
Environment:
  - DATABASE_URL: (from Secret Manager)
  - REDIS_URL: (from Secret Manager)
  - OPENCLAW_GATEWAY_URL: ws://gateway-ip:18789
```

#### 2. Cloud Run (Frontend)

```yaml
Service: mission-control-frontend
Memory: 512Mi
CPU: 1
Min Instances: 1
Max Instances: 50
Environment:
  - NEXT_PUBLIC_API_URL: https://api.mission-control.com
```

#### 3. Cloud SQL

```yaml
Instance: mission-control-db
Type: PostgreSQL 16
Tier: db-f1-micro (dev) / db-n1-standard-1 (prod)
Storage: 10GB SSD
Backups: Daily, 7-day retention
High Availability: Regional (prod only)
Private IP: Yes
```

#### 4. Memorystore (Redis)

```yaml
Instance: mission-control-cache
Tier: Basic (dev) / Standard (prod)
Memory: 1GB (dev) / 4GB (prod)
Version: Redis 7.0
Private IP: Yes
```

### Deployment Scripts

#### Deploy Backend

```bash
#!/bin/bash
# infra/scripts/deploy-backend.sh

PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_NAME="mission-control-backend"

# Build and push image
gcloud builds submit \
  --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  ./backend

# Deploy to Cloud Run
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 100 \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production" \
  --set-secrets "DATABASE_URL=database-url:latest" \
  --set-secrets "REDIS_URL=redis-url:latest" \
  --set-secrets "OPENCLAW_TOKEN=openclaw-token:latest"
```

#### Deploy Frontend

```bash
#!/bin/bash
# infra/scripts/deploy-frontend.sh

PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_NAME="mission-control-frontend"

# Build and push image
gcloud builds submit \
  --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  ./frontend

# Deploy to Cloud Run
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 50 \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_API_URL=https://api.mission-control.com"
```

### Terraform Configuration

```hcl
# infra/terraform/main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud SQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "mission-control-db"
  database_version = "POSTGRES_16"
  region          = var.region

  settings {
    tier = var.environment == "prod" ? "db-n1-standard-1" : "db-f1-micro"
    
    backup_configuration {
      enabled = true
      start_time = "03:00"
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
  }
}

# Cloud SQL Database
resource "google_sql_database" "mission_control" {
  name     = "mission_control"
  instance = google_sql_database_instance.postgres.name
}

# Redis Instance
resource "google_redis_instance" "cache" {
  name           = "mission-control-cache"
  tier           = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.environment == "prod" ? 4 : 1
  region         = var.region
  
  redis_version = "REDIS_7_0"
  display_name  = "Mission Control Cache"
  
  authorized_network = google_compute_network.vpc.id
}

# Cloud Run Service - Backend
resource "google_cloud_run_service" "backend" {
  name     = "mission-control-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/mission-control-backend"
        
        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }
        
        env {
          name = "ENVIRONMENT"
          value = var.environment
        }
      }
    }
  }
}

# Cloud Run Service - Frontend
resource "google_cloud_run_service" "frontend" {
  name     = "mission-control-frontend"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/mission-control-frontend"
        
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
        
        env {
          name = "NEXT_PUBLIC_API_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
      }
    }
  }
}
```

### Monitoring & Observability

#### Metrics to Track

1. **Application Metrics**
   - Request latency (p50, p95, p99)
   - Request rate
   - Error rate
   - Active connections

2. **Infrastructure Metrics**
   - CPU utilization
   - Memory usage
   - Database connections
   - Redis operations/sec

3. **Business Metrics**
   - Active agents
   - Jobs per hour
   - Task completion rate
   - SSE connections

#### Alerting Rules

```yaml
alerts:
  - name: HighErrorRate
    condition: error_rate > 1%
    duration: 5m
    severity: warning
    
  - name: HighLatency
    condition: p95_latency > 1s
    duration: 5m
    severity: warning
    
  - name: DatabaseConnectionPool
    condition: connection_pool_usage > 80%
    duration: 5m
    severity: critical
    
  - name: OpenClawDisconnected
    condition: openclaw_connected == 0
    duration: 1m
    severity: critical
```

### Security Best Practices

1. **Network Security**
   - Use Private Service Connect for internal communication
   - Enable Cloud Armor for DDoS protection
   - Implement VPC Service Controls

2. **Data Security**
   - Enable encryption at rest for all services
   - Use Cloud KMS for key management
   - Regular security scanning with Cloud Security Scanner

3. **Access Control**
   - Use IAM for service accounts
   - Implement least privilege principle
   - Enable audit logging

4. **Secrets Management**
   - Store all secrets in Secret Manager
   - Rotate credentials regularly
   - Never commit secrets to git

### Cost Optimization

1. **Development Environment**
   - Use preemptible instances
   - Scale to zero when idle
   - Use shared core instances

2. **Production Environment**
   - Use committed use discounts
   - Enable autoscaling
   - Optimize image sizes
   - Use Cloud CDN for static assets

3. **Estimated Monthly Costs**

```
Development:
- Cloud Run: ~$10
- Cloud SQL: ~$15
- Redis: ~$25
- Total: ~$50/month

Production:
- Cloud Run: ~$100-500
- Cloud SQL: ~$100
- Redis: ~$100
- Load Balancer: ~$25
- Total: ~$325-725/month
```

### Disaster Recovery

1. **Backup Strategy**
   - Daily automated PostgreSQL backups
   - 7-day retention for development
   - 30-day retention for production
   - Cross-region backup replication

2. **Recovery Procedures**
   - RPO: 24 hours
   - RTO: 4 hours
   - Automated failover for Redis
   - Manual failover for PostgreSQL

3. **Testing**
   - Quarterly DR drills
   - Automated backup verification
   - Failover testing

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - id: auth
      uses: google-github-actions/auth@v1
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}
    
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
    
    - name: Deploy Backend
      run: |
        gcloud builds submit --tag gcr.io/${{ env.PROJECT_ID }}/backend ./backend
        gcloud run deploy backend --image gcr.io/${{ env.PROJECT_ID }}/backend
    
    - name: Deploy Frontend
      run: |
        gcloud builds submit --tag gcr.io/${{ env.PROJECT_ID }}/frontend ./frontend
        gcloud run deploy frontend --image gcr.io/${{ env.PROJECT_ID }}/frontend
```

## Support

For infrastructure issues:
- Check logs in Cloud Logging
- Review metrics in Cloud Monitoring
- Contact: devops@yourcompany.com