# Phase 08: Deployment & Operations

## Context Links

- Phase 07: `phase-07-testing-performance-validation.md`
- Architecture: `ARCHITECTURE.md`
- Summary: `SUMMARY.md`

## Overview

**Priority:** High (FINAL PHASE)  
**Status:** Planned  
**Goal:** Deploy the system to production, document operations, and establish monitoring/maintenance procedures.

## Requirements

### Deployment

- Setup MacBook Pro 2017 as production server
- Configure Cloudflare Tunnel
- Setup auto-start services (launchd)
- Configure firewall and security
- Setup backup strategy

### Documentation

- Deployment guide
- Operations manual
- Troubleshooting guide
- User guide

### Monitoring

- Health check monitoring
- Error logging
- Performance metrics
- Alerting (optional)

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ MacBook Pro 2017 (Production Server)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FastAPI Web Server                                     │ │
│  │ - Port: 8000 (localhost only)                          │ │
│  │ - Workers: 2                                           │ │
│  │ - Auto-restart: launchd                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                            ↓                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Cloudflare Tunnel                                      │ │
│  │ - Tunnel: danangvibes                                  │ │
│  │ - Auto-restart: launchd                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                            ↓                                 │
│                   Internet (HTTPS)                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   https://danangvibes.com
```

## Server Setup

### 1. System Requirements

**MacBook Pro 2017:**
- macOS 12+ (Monterey or later)
- 8GB RAM minimum
- 256GB SSD minimum (500GB+ recommended)
- Stable internet connection
- Power adapter (always plugged in)

### 2. Initial Setup

```bash
# Update system
sudo softwareupdate -i -a

# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Create project directory
mkdir -p ~/danangvibes
cd ~/danangvibes

# Clone repository
git clone <repo-url> .

# Setup web server
cd web_server
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create storage directories
sudo mkdir -p /Volumes/SSD/events
sudo mkdir -p /Volumes/SSD/incoming
sudo chown -R $(whoami) /Volumes/SSD/events
sudo chown -R $(whoami) /Volumes/SSD/incoming

# Create logs directory
mkdir -p ~/logs
```

### 3. Environment Configuration

File: `web_server/.env`

```bash
# Server
DANANGVIBES_HOST=127.0.0.1
DANANGVIBES_PORT=8000
DANANGVIBES_WORKERS=2

# Storage
DANANGVIBES_STORAGE_PATH=/Volumes/SSD/events
DANANGVIBES_SERVER_DB_PATH=/Volumes/SSD/events/server.db

# Admin
DANANGVIBES_ADMIN_TOKEN=<generate-strong-token>

# Cloudflare
DANANGVIBES_CLOUDFLARE_TUNNEL_NAME=danangvibes
DANANGVIBES_CLOUDFLARE_TUNNEL_TOKEN=<your-tunnel-token>

# Logging
DANANGVIBES_LOG_LEVEL=INFO
DANANGVIBES_LOG_FILE=/Users/admin/logs/danangvibes.log
```

**Generate admin token:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Cloudflare Tunnel Setup

```bash
# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create danangvibes

# Configure tunnel
cat > ~/.cloudflared/config.yml <<EOF
tunnel: danangvibes
credentials-file: /Users/admin/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: danangvibes.com
    service: http://localhost:8000
  - hostname: www.danangvibes.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Route DNS
cloudflared tunnel route dns danangvibes danangvibes.com
cloudflared tunnel route dns danangvibes www.danangvibes.com

# Test tunnel
cloudflared tunnel run danangvibes
```

### 5. Auto-Start Services (launchd)

**Web Server Service**

File: `~/Library/LaunchAgents/com.danangvibes.server.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.danangvibes.server</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/admin/danangvibes/web_server/venv/bin/python</string>
        <string>-m</string>
        <string>web_server</string>
        <string>run</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
        <string>--storage-path</string>
        <string>/Volumes/SSD/events</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/admin/danangvibes/web_server</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/admin/danangvibes/web_server/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/Users/admin/logs/danangvibes.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/admin/logs/danangvibes.error.log</string>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

**Cloudflare Tunnel Service**

File: `~/Library/LaunchAgents/com.danangvibes.tunnel.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.danangvibes.tunnel</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/cloudflared</string>
        <string>tunnel</string>
        <string>run</string>
        <string>danangvibes</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/Users/admin/logs/cloudflared.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/admin/logs/cloudflared.error.log</string>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

**Load services:**

```bash
# Load web server
launchctl load ~/Library/LaunchAgents/com.danangvibes.server.plist

# Load tunnel
launchctl load ~/Library/LaunchAgents/com.danangvibes.tunnel.plist

# Check status
launchctl list | grep danangvibes

# View logs
tail -f ~/logs/danangvibes.log
tail -f ~/logs/cloudflared.log
```

## Operations Manual

### Daily Operations

**Check System Health:**
```bash
# Check services running
launchctl list | grep danangvibes

# Check health endpoint
curl http://localhost:8000/health

# Check logs for errors
tail -n 100 ~/logs/danangvibes.error.log
```

**Monitor Resources:**
```bash
# Memory usage
ps aux | grep python

# Disk usage
df -h /Volumes/SSD

# Network
netstat -an | grep 8000
```

### Event Operations

**Import New Event:**

```bash
# 1. Receive bundle from M1 (via SSD/rsync)
# Assume bundle copied to /Volumes/SSD/incoming/ironman-danang-2026

# 2. Import bundle
cd ~/danangvibes/web_server
source venv/bin/activate
python -m web_server import \
  --bundle /Volumes/SSD/incoming/ironman-danang-2026 \
  --storage-path /Volumes/SSD/events

# 3. Review OCR (via admin UI)
# Open: https://danangvibes.com/admin/events/ironman-danang-2026/ocr-review

# 4. Configure donation
# Open: https://danangvibes.com/admin/events/ironman-danang-2026/config

# 5. Publish event
python -m web_server publish --event-slug ironman-danang-2026

# 6. Verify public access
# Open: https://danangvibes.com/events/ironman-danang-2026
```

**Update Event:**

```bash
# 1. Import new version
python -m web_server import \
  --bundle /Volumes/SSD/incoming/ironman-danang-2026-v2 \
  --storage-path /Volumes/SSD/events \
  --version v2

# 2. Switch to new version
python -m web_server switch-version \
  --event-slug ironman-danang-2026 \
  --version v2

# 3. If issues, rollback
python -m web_server rollback \
  --event-slug ironman-danang-2026 \
  --version v1
```

**Unpublish Event:**

```bash
python -m web_server unpublish --event-slug ironman-danang-2026
```

### Maintenance

**Restart Services:**

```bash
# Restart web server
launchctl unload ~/Library/LaunchAgents/com.danangvibes.server.plist
launchctl load ~/Library/LaunchAgents/com.danangvibes.server.plist

# Restart tunnel
launchctl unload ~/Library/LaunchAgents/com.danangvibes.tunnel.plist
launchctl load ~/Library/LaunchAgents/com.danangvibes.tunnel.plist
```

**Update Code:**

```bash
cd ~/danangvibes
git pull origin main

# Restart services
launchctl unload ~/Library/LaunchAgents/com.danangvibes.server.plist
launchctl load ~/Library/LaunchAgents/com.danangvibes.server.plist
```

**Rotate Logs:**

```bash
# Create log rotation script
cat > ~/scripts/rotate_logs.sh <<'EOF'
#!/bin/bash
LOG_DIR=~/logs
DATE=$(date +%Y%m%d)

# Rotate logs older than 7 days
find $LOG_DIR -name "*.log" -mtime +7 -exec gzip {} \;
find $LOG_DIR -name "*.log.gz" -mtime +30 -delete

# Rotate current logs if > 100MB
for log in $LOG_DIR/*.log; do
  size=$(stat -f%z "$log")
  if [ $size -gt 104857600 ]; then
    mv "$log" "$log.$DATE"
    gzip "$log.$DATE"
  fi
done
EOF

chmod +x ~/scripts/rotate_logs.sh

# Add to crontab (run daily at 2am)
crontab -e
# Add: 0 2 * * * ~/scripts/rotate_logs.sh
```

## Backup Strategy

### What to Backup

1. **Server database:** `/Volumes/SSD/events/server.db`
2. **Event bundles:** `/Volumes/SSD/events/*/releases/`
3. **Donation QR codes:** `web_server/static/uploads/qr/`
4. **Configuration:** `web_server/.env`, `.cloudflared/config.yml`

### Backup Script

File: `~/scripts/backup.sh`

```bash
#!/bin/bash

BACKUP_DIR=/Volumes/Backup/danangvibes
DATE=$(date +%Y%m%d)
BACKUP_PATH=$BACKUP_DIR/$DATE

mkdir -p $BACKUP_PATH

# Backup server database
cp /Volumes/SSD/events/server.db $BACKUP_PATH/

# Backup event bundles (metadata only, not originals)
rsync -av --exclude='originals' \
  /Volumes/SSD/events/ \
  $BACKUP_PATH/events/

# Backup QR codes
rsync -av ~/danangvibes/web_server/static/uploads/qr/ \
  $BACKUP_PATH/qr/

# Backup config
cp ~/danangvibes/web_server/.env $BACKUP_PATH/
cp ~/.cloudflared/config.yml $BACKUP_PATH/

# Compress
cd $BACKUP_DIR
tar -czf $DATE.tar.gz $DATE
rm -rf $DATE

# Keep only last 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/$DATE.tar.gz"
```

**Schedule backup:**

```bash
chmod +x ~/scripts/backup.sh

# Add to crontab (run daily at 3am)
crontab -e
# Add: 0 3 * * * ~/scripts/backup.sh
```

## Monitoring

### Health Check Monitoring

**Simple monitoring script:**

File: `~/scripts/monitor.sh`

```bash
#!/bin/bash

HEALTH_URL="http://localhost:8000/health"
ALERT_EMAIL="admin@example.com"

# Check health endpoint
response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $response -ne 200 ]; then
  echo "Health check failed: HTTP $response" | mail -s "DaNang Vibes Alert" $ALERT_EMAIL
  
  # Try to restart
  launchctl unload ~/Library/LaunchAgents/com.danangvibes.server.plist
  sleep 5
  launchctl load ~/Library/LaunchAgents/com.danangvibes.server.plist
fi
```

**Schedule monitoring:**

```bash
chmod +x ~/scripts/monitor.sh

# Add to crontab (run every 5 minutes)
crontab -e
# Add: */5 * * * * ~/scripts/monitor.sh
```

### Log Monitoring

**Check for errors:**

```bash
# Recent errors
tail -n 100 ~/logs/danangvibes.error.log

# Count errors today
grep "ERROR" ~/logs/danangvibes.log | grep "$(date +%Y-%m-%d)" | wc -l

# Search for specific error
grep "Face search failed" ~/logs/danangvibes.log
```

## Troubleshooting Guide

### Server Won't Start

**Symptoms:** Service not running, can't access http://localhost:8000

**Diagnosis:**
```bash
# Check service status
launchctl list | grep danangvibes

# Check error logs
tail -n 50 ~/logs/danangvibes.error.log

# Check port in use
lsof -i :8000
```

**Solutions:**
1. Port 8000 already in use → kill process or change port
2. Python venv broken → recreate venv
3. Missing dependencies → `pip install -r requirements.txt`
4. Permission issues → check file ownership

### Cloudflare Tunnel Down

**Symptoms:** Can't access https://danangvibes.com

**Diagnosis:**
```bash
# Check tunnel status
launchctl list | grep tunnel

# Check tunnel logs
tail -n 50 ~/logs/cloudflared.log

# Test local server
curl http://localhost:8000/health
```

**Solutions:**
1. Tunnel service crashed → restart service
2. Cloudflare token expired → regenerate token
3. DNS not configured → check Cloudflare dashboard

### Slow Performance

**Symptoms:** Search takes > 5s, high memory usage

**Diagnosis:**
```bash
# Check memory
ps aux | grep python

# Check CPU
top -pid $(pgrep -f "web_server")

# Check disk I/O
iostat -d 1
```

**Solutions:**
1. Too many events loaded → unpublish old events
2. Memory leak → restart service
3. Disk full → clean up old bundles
4. FAISS index too large → optimize index

### Search Returns No Results

**Symptoms:** Bib/face search returns empty

**Diagnosis:**
```bash
# Check event published
curl http://localhost:8000/admin/events

# Check bundle loaded
curl http://localhost:8000/health

# Check database
sqlite3 /Volumes/SSD/events/ironman-danang-2026/active/event.db "SELECT COUNT(*) FROM photos;"
```

**Solutions:**
1. Event not published → publish event
2. Bundle not imported → import bundle
3. OCR data missing → reprocess event
4. FAISS index corrupt → rebuild index

## Security Checklist

- [ ] Admin token is strong (32+ characters)
- [ ] Admin token stored in .env (not hardcoded)
- [ ] .env file not committed to git
- [ ] Cloudflare Tunnel token secure
- [ ] Server only listens on localhost (not 0.0.0.0)
- [ ] Firewall enabled
- [ ] macOS auto-updates enabled
- [ ] Regular backups configured
- [ ] Logs don't contain sensitive data

## Documentation

### User Guide

Create: `docs/user-guide.md`

**Contents:**
- How to search for photos
- How to download photos
- How to donate
- FAQ
- Contact support

### Admin Guide

Create: `docs/admin-guide.md`

**Contents:**
- How to import events
- How to review OCR
- How to configure donations
- How to publish/unpublish events
- How to view analytics

## Implementation Steps

1. **Setup production server** (1 day)
2. **Configure Cloudflare Tunnel** (0.5 day)
3. **Setup auto-start services** (0.5 day)
4. **Test deployment** (1 day)
5. **Write operations manual** (1 day)
6. **Write troubleshooting guide** (1 day)
7. **Setup monitoring** (1 day)
8. **Setup backups** (0.5 day)
9. **Write user documentation** (1 day)
10. **Final validation** (1 day)

## Todo List

- [ ] Setup MacBook Pro 2017
- [ ] Install dependencies
- [ ] Configure environment
- [ ] Setup Cloudflare Tunnel
- [ ] Create launchd services
- [ ] Test auto-start
- [ ] Setup log rotation
- [ ] Setup backups
- [ ] Setup monitoring
- [ ] Write operations manual
- [ ] Write troubleshooting guide
- [ ] Write user guide
- [ ] Test full deployment
- [ ] Import first real event
- [ ] Validate public access

## Success Criteria

- [ ] Server auto-starts on boot
- [ ] Cloudflare Tunnel works
- [ ] Public URL accessible
- [ ] Health check passes
- [ ] Backups running daily
- [ ] Monitoring alerts work
- [ ] Documentation complete
- [ ] First event published successfully

## Post-Launch

### Week 1
- Monitor logs daily
- Check performance metrics
- Gather user feedback
- Fix critical bugs

### Month 1
- Review analytics
- Optimize based on usage patterns
- Update documentation
- Plan improvements

### Ongoing
- Monthly backups verification
- Quarterly security review
- Update dependencies
- Add new features based on feedback

## Next Steps

After deployment complete:
- Launch first event
- Gather user feedback
- Iterate on UX
- Plan Phase 2 features

## Unresolved Questions

- Should we use external monitoring service (UptimeRobot)? → Optional, simple cron monitoring OK for MVP
- Should we setup email alerts? → Optional, logs + manual check OK for MVP
