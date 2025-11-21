# Changelog

All notable changes to the RobianAPI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive issue documentation in `docs/ISSUES_FIXED.md`
- Analysis summary document in `docs/ANALYSIS_SUMMARY.md`
- Development notes in `docs/DEVELOPMENT_NOTES.md`

### Fixed
- **CRITICAL**: SECRET_KEY configuration crash - added development default
- **CRITICAL**: Windows compatibility - os.getuid() wrapped in try-except
- **CRITICAL**: Pydantic v2 configuration errors - added model_config to all Settings classes
- **HIGH**: Missing created_at/updated_at timestamps in database models
- **HIGH**: CORS middleware type mismatch - now uses cors_origins_list property
- **MEDIUM**: Typo in environment variable (RATE_LIBMIT_BURST → RATE_LIMIT_BURST)
- **MEDIUM**: PostgreSQL array search syntax - using .contains() instead of .any()
- **MEDIUM**: Background task database session leak - now creates independent session
- Database models now properly include timestamp fields for audit trail

### Changed
- Documentation reorganized into `docs/` directory
- Updated README.md with current project status
- All Settings classes now use Pydantic v2 model_config

## [1.0.0] - 2025-11-21

### Added
- Initial FastAPI backend with 12+ REST endpoints
- PostgreSQL database integration with SQLAlchemy 2.0
- Redis multi-tier caching with memory fallback
- WebSocket service for real-time notifications
- Audio extraction pipeline (yt-dlp + FFmpeg)
- Docker and Docker Compose configuration
- Comprehensive middleware stack (CORS, rate limiting, logging, security headers)
- Multi-platform support (Linux, macOS, Windows)
- Health check endpoints with detailed system status
- Structured logging with configurable formats
- Environment-based configuration system

### Security
- Rate limiting per endpoint
- CORS configuration with origin validation
- Security headers (HSTS, CSP, XSS Protection)
- Non-root Docker container execution

## [0.1.0] - 2024-06-09

### Added
- Initial project structure
- Basic API endpoints (legacy)
- Audio extraction scripts
- Database setup scripts
- Docker configuration
- Environment configuration examples

---

## Migration Notes

### Upgrading to 1.0.0

If you have an existing database, you need to add timestamp columns:

```sql
-- Add timestamps to existing tables
ALTER TABLE debates
  ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL;

ALTER TABLE audio_files
  ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL;

ALTER TABLE scheduled_sessions
  ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL;

-- Add auto-update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_debates_updated_at
    BEFORE UPDATE ON debates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audio_files_updated_at
    BEFORE UPDATE ON audio_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduled_sessions_updated_at
    BEFORE UPDATE ON scheduled_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Environment Variables

Ensure you set the following in production:

```bash
SECRET_KEY=<generate-secure-random-key>
POSTGRES_PASSWORD=<strong-password>
BACKEND_CORS_ORIGINS=https://yourdomain.com
ENVIRONMENT=production
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

**Note:** For detailed information about specific bug fixes, see `docs/ISSUES_FIXED.md`
