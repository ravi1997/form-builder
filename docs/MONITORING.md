# Infrastructure Monitoring Dashboard Configuration
# This file contains configuration for monitoring the Form Builder Platform

## Grafana Dashboard Configuration

### General Settings
- **Dashboard Title**: Form Builder Platform - Infrastructure Monitoring
- **Description**: Comprehensive monitoring dashboard for the Form Builder Platform services and infrastructure
- **Tags**: form-builder, infrastructure, monitoring, production
- **Time Range**: Last 1 hour (default)
- **Refresh**: 30s

### Variables

#### Environment Variable
- **Name**: environment
- **Type**: Custom
- **Values**: development, testing, production
- **Default**: production

#### Host Variable
- **Name**: host
- **Type**: Query
- **Data Source**: Prometheus
- **Query**: label_values(up{job="form-builder"}, instance)

### Panels

#### 1. System Overview (Row)
**Title**: System Overview
**Collapsible**: true

##### 1.1 System Health Status
- **Title**: System Health Status
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  count(up{job="form-builder"})
  ```
- **Color**: Green if > 0, Red if = 0
- **Value Mapping**: 
  - 0: "DOWN"
  - 1+: "UP"

##### 1.2 Uptime
- **Title**: System Uptime
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  time() - process_start_time_seconds{job="form-builder-backend"}
  ```
- **Unit**: seconds
- **Visualization**: Duration

#### 2. Resource Usage (Row)
**Title**: Resource Usage
**Collapsible**: true

##### 2.1 CPU Usage
- **Title**: CPU Usage (%)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[$__rate_interval])) * 100)
  ```
- **Legend**: {{instance}}
- **Y-axis**: 0-100
- **Unit**: percent (%)

##### 2.2 Memory Usage
- **Title**: Memory Usage (%)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  100 * (1 - ((node_memory_MemAvailable_bytes or node_memory_MemFree_bytes + node_memory_Buffers_bytes + node_memory_Cached_bytes) / node_memory_MemTotal_bytes))
  ```
- **Legend**: {{instance}}
- **Y-axis**: 0-100
- **Unit**: percent (%)

##### 2.3 Disk Usage
- **Title**: Disk Usage (%)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
  ```
- **Legend**: {{mountpoint}}
- **Y-axis**: 0-100
- **Unit**: percent (%)

##### 2.4 Network Traffic
- **Title**: Network Traffic
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  irate(node_network_receive_bytes_total[$__rate_interval])
  ```
- **Legend**: {{device}} Receive
- **Unit**: bytes/sec

#### 3. Application Services (Row)
**Title**: Application Services
**Collapsible**: true

##### 3.1 Service Status
- **Title**: Service Status
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  up{job=~"form-builder-.*"}
  ```
- **Color by field**: Value
- **Value Mapping**: 
  - 0: "DOWN"
  - 1: "UP"

##### 3.2 HTTP Request Rate
- **Title**: HTTP Request Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(http_requests_total[$__rate_interval])
  ```
- **Legend**: {{method}} {{status}} {{endpoint}}
- **Unit**: requests/sec

##### 3.3 HTTP Response Time
- **Title**: HTTP Response Time (P95)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[$__rate_interval]))
  ```
- **Legend**: {{endpoint}}
- **Unit**: seconds

##### 3.4 HTTP Error Rate
- **Title**: HTTP Error Rate (%)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  (rate(http_requests_total{status=~"5.."}[$__rate_interval]) / rate(http_requests_total[$__rate_interval])) * 100
  ```
- **Legend**: {{status}}
- **Y-axis**: 0-100
- **Unit**: percent (%)

#### 4. Database Services (Row)
**Title**: Database Services
**Collapsible**: true

##### 4.1 MongoDB Status
- **Title**: MongoDB Status
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  up{job="mongodb"}
  ```
- **Color**: Green if = 1, Red if = 0

##### 4.2 MongoDB Connections
- **Title**: MongoDB Connections
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  mongodb_connections{job="mongodb"}
  ```
- **Legend**: {{state}}
- **Unit**: connections

##### 4.3 MongoDB Operations
- **Title**: MongoDB Operations Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(mongodb_op_counters_total[$__rate_interval])
  ```
- **Legend**: {{op}}
- **Unit**: ops/sec

##### 4.4 Redis Status
- **Title**: Redis Status
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  up{job="redis"}
  ```
- **Color**: Green if = 1, Red if = 0

##### 4.5 Redis Memory Usage
- **Title**: Redis Memory Usage
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  redis_memory_used_bytes{job="redis"}
  ```
- **Legend**: {{instance}}
- **Unit**: bytes

##### 4.6 Redis Operations
- **Title**: Redis Operations Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(redis_commands_total[$__rate_interval])
  ```
- **Legend**: {{cmd}}
- **Unit**: ops/sec

#### 5. Search Engine (Row)
**Title**: Search Engine
**Collapsible**: true

##### 5.1 Elasticsearch Status
- **Title**: Elasticsearch Status
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  up{job="elasticsearch"}
  ```
- **Color**: Green if = 1, Red if = 0

##### 5.2 Elasticsearch Cluster Health
- **Title**: Elasticsearch Cluster Health
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  elasticsearch_cluster_health_status{job="elasticsearch"}
  ```
- **Color by field**: Value
- **Value Mapping**: 
  - 0: "Red"
  - 1: "Yellow"
  - 2: "Green"

##### 5.3 Elasticsearch Index Rate
- **Title**: Elasticsearch Index Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(elasticsearch_indices_indexing_index_total[$__rate_interval])
  ```
- **Legend**: {{index}}
- **Unit**: docs/sec

##### 5.4 Elasticsearch Search Rate
- **Title**: Elasticsearch Search Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(elasticsearch_indices_search_query_total[$__rate_interval])
  ```
- **Legend**: {{index}}
- **Unit**: queries/sec

#### 6. Task Queue (Row)
**Title**: Task Queue
**Collapsible**: true

##### 6.1 Celery Worker Status
- **Title**: Celery Worker Status
- **Type**: Stat
- **Data Source**: Prometheus
- **Query**: 
  ```
  up{job="celery"}
  ```
- **Color**: Green if = 1, Red if = 0

##### 6.2 Celery Task Rate
- **Title**: Celery Task Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(celery_tasks_total[$__rate_interval])
  ```
- **Legend**: {{name}} {{status}}
- **Unit**: tasks/sec

##### 6.3 Celery Task Duration
- **Title**: Celery Task Duration (P95)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  histogram_quantile(0.95, rate(celery_task_duration_seconds_bucket[$__rate_interval]))
  ```
- **Legend**: {{name}}
- **Unit**: seconds

##### 6.4 Celery Queue Length
- **Title**: Celery Queue Length
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  celery_queue_length
  ```
- **Legend**: {{queue}}
- **Unit**: tasks

#### 7. File Uploads (Row)
**Title**: File Uploads
**Collapsible**: true

##### 7.1 Upload Rate
- **Title**: Upload Rate
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  rate(file_uploads_total[$__rate_interval])
  ```
- **Legend**: {{status}}
- **Unit**: uploads/sec

##### 7.2 Upload Size
- **Title**: Upload Size (P95)
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  histogram_quantile(0.95, rate(file_upload_size_bytes_bucket[$__rate_interval]))
  ```
- **Legend**: {{file_type}}
- **Unit**: bytes

##### 7.3 Storage Usage
- **Title**: Storage Usage
- **Type**: Graph
- **Data Source**: Prometheus
- **Query**: 
  ```
  storage_usage_bytes{org_id!=""}
  ```
- **Legend**: {{org_id}}
- **Unit**: bytes

#### 8. Alerts (Row)
**Title**: Alerts
**Collapsible**: true

##### 8.1 Active Alerts
- **Title**: Active Alerts
- **Type**: Table
- **Data Source**: Alertmanager
- **Query**: 
  ```
  ALERTS{alertstate="firing"}
  ```
- **Columns**: Alertname, Severity, Summary, Starts At

##### 8.2 Alert History
- **Title**: Alert History
- **Type**: Table
- **Data Source**: Prometheus
- **Query**: 
  ```
  increases(ALERTS{alertstate="firing"}[$__interval])
  ```
- **Columns**: Alertname, Severity, Count

### Annotations

#### Deployments
- **Name**: Deployments
- **Data Source**: Prometheus
- **Query**: 
  ```
  deployment_timestamp
  ```
- **Tags**: deployment, version

#### Alerts
- **Name**: Alerts
- **Data Source**: Alertmanager
- **Query**: 
  ```
  ALERTS
  ```
- **Tags**: alert

### Template Variables

#### Time Range
- **Name**: interval
- **Type**: Interval
- **Values**: 30s, 1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d
- **Default**: 30s

#### Refresh
- **Name**: refresh
- **Type**: Interval
- **Values**: 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h
- **Default**: 30s

### Links

#### Documentation
- **Title**: Documentation
- **URL**: https://yourdomain.com/docs
- **Icon**: doc

#### API Docs
- **Title**: API Docs
- **URL**: https://yourdomain.com/api/docs
- **Icon**: api

#### Flower
- **Title**: Celery Flower
- **URL**: http://localhost:5555
- **Icon**: dashboard

#### Kibana
- **Title**: Kibana
- **URL**: http://localhost:5601
- **Icon**: dashboard

## Prometheus Configuration

### Global Settings
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Scrape Configurations

#### Form Builder Backend
```yaml
- job_name: 'form-builder-backend'
  static_configs:
    - targets: ['backend:5000']
  metrics_path: '/metrics'
  scrape_interval: 15s
```

#### Node Exporter
```yaml
- job_name: 'node'
  static_configs:
    - targets: ['node-exporter:9100']
  scrape_interval: 15s
```

#### MongoDB Exporter
```yaml
- job_name: 'mongodb'
  static_configs:
    - targets: ['mongodb-exporter:9216']
  scrape_interval: 15s
```

#### Redis Exporter
```yaml
- job_name: 'redis'
  static_configs:
    - targets: ['redis-exporter:9121']
  scrape_interval: 15s
```

#### Elasticsearch Exporter
```yaml
- job_name: 'elasticsearch'
  static_configs:
    - targets: ['elasticsearch-exporter:9114']
  scrape_interval: 15s
```

#### Celery Exporter
```yaml
- job_name: 'celery'
  static_configs:
    - targets: ['celery-exporter:9540']
  scrape_interval: 15s
```

## Alert Rules

### System Alerts

#### High CPU Usage
```yaml
- alert: HighCpuUsage
  expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High CPU usage on {{ $labels.instance }}"
    description: "CPU usage is {{ $value }}% for more than 5 minutes"
```

#### High Memory Usage
```yaml
- alert: HighMemoryUsage
  expr: (1 - ((node_memory_MemAvailable_bytes or node_memory_MemFree_bytes + node_memory_Buffers_bytes + node_memory_Cached_bytes) / node_memory_MemTotal_bytes)) * 100 > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High memory usage on {{ $labels.instance }}"
    description: "Memory usage is {{ $value }}% for more than 5 minutes"
```

#### High Disk Usage
```yaml
- alert: HighDiskUsage
  expr: (1 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})) > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High disk usage on {{ $labels.instance }}"
    description: "Disk usage is {{ $value }}% for more than 5 minutes"
```

### Application Alerts

#### Service Down
```yaml
- alert: ServiceDown
  expr: up{job=~"form-builder-.*"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "{{ $labels.job }} service is down"
    description: "{{ $labels.job }} service has been down for more than 1 minute"
```

#### High HTTP Error Rate
```yaml
- alert: HighHttpErrorRate
  expr: (rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) * 100 > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High HTTP error rate"
    description: "HTTP error rate is {{ $value }}% for more than 5 minutes"
```

#### High HTTP Response Time
```yaml
- alert: HighHttpResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High HTTP response time"
    description: "HTTP response time (P95) is {{ $value }} seconds for more than 5 minutes"
```

### Database Alerts

#### MongoDB Down
```yaml
- alert: MongoDBDown
  expr: up{job="mongodb"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "MongoDB is down"
    description: "MongoDB service has been down for more than 1 minute"
```

#### Redis Down
```yaml
- alert: RedisDown
  expr: up{job="redis"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Redis is down"
    description: "Redis service has been down for more than 1 minute"
```

#### Elasticsearch Down
```yaml
- alert: ElasticsearchDown
  expr: up{job="elasticsearch"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Elasticsearch is down"
    description: "Elasticsearch service has been down for more than 1 minute"
```

### Task Queue Alerts

#### Celery Worker Down
```yaml
- alert: CeleryWorkerDown
  expr: up{job="celery"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Celery worker is down"
    description: "Celery worker service has been down for more than 1 minute"
```

#### High Celery Task Queue Length
```yaml
- alert: HighCeleryTaskQueueLength
  expr: celery_queue_length > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High Celery task queue length"
    description: "Celery task queue length is {{ $value }} tasks for more than 5 minutes"
```

#### Slow Celery Tasks
```yaml
- alert: SlowCeleryTasks
  expr: histogram_quantile(0.95, rate(celery_task_duration_seconds_bucket[5m])) > 60
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Slow Celery tasks"
    description: "Celery task duration (P95) is {{ $value }} seconds for more than 5 minutes"
```

## Docker Compose Monitoring Services

### Prometheus
```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - ./monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml
    - prometheus_data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.console.libraries=/etc/prometheus/console_libraries'
    - '--web.console.templates=/etc/prometheus/consoles'
    - '--storage.tsdb.retention.time=30d'
    - '--web.enable-lifecycle'
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### Grafana
```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_USERS_ALLOW_SIGN_UP=false
  volumes:
    - grafana_data:/var/lib/grafana
    - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### Alertmanager
```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  volumes:
    - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    - alertmanager_data:/alertmanager
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### Node Exporter
```yaml
node-exporter:
  image: prom/node-exporter:latest
  ports:
    - "9100:9100"
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /:/rootfs:ro
  command:
    - '--path.procfs=/host/proc'
    - '--path.rootfs=/rootfs'
    - '--path.sysfs=/host/sys'
    - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### MongoDB Exporter
```yaml
mongodb-exporter:
  image: bitnami/mongodb-exporter:latest
  ports:
    - "9216:9216"
  environment:
    - MONGODB_URI=mongodb://mongodb:27017
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### Redis Exporter
```yaml
redis-exporter:
  image: oliver006/redis_exporter:latest
  ports:
    - "9121:9121"
  environment:
    - REDIS_ADDR=redis://redis:6379
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### Elasticsearch Exporter
```yaml
elasticsearch-exporter:
  image: prometheuscommunity/elasticsearch-exporter:latest
  ports:
    - "9114:9114"
  command:
    - '--es.uri=http://elasticsearch:9200'
  restart: unless-stopped
  networks:
    - formbuilder_network
```

### Celery Exporter
```yaml
celery-exporter:
  image: prometheus/celery-exporter:latest
  ports:
    - "9540:9540"
  command:
    - '--celery-broker=redis://redis:6379/0'
    - '--celery-backend=redis://redis:6379/0'
  restart: unless-stopped
  networks:
    - formbuilder_network
```