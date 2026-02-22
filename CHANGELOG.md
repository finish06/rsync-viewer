# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

## [1.3.0] - 2026-02-22

### Added

- Add failure detection with exit code tracking and stale sync monitoring
- Add webhook notification service with retry logic and auto-disable
- Add Discord integration with rich embeds, source filters, and rate limiting
- Add webhook settings UI with HTMX CRUD (add/edit/delete/toggle/test)
- Add webhook settings UI tests (21 tests covering AC-007)
- Add monitor last_sync_at update integration test

### Changed

- Debounce API key writes, fix stale checker N+1 queries, add database indexes
- Add webhook.enabled index and reduce DB commits in HTMX handlers
- Fix N+1 queries and reduce excessive DB commits in Discord integration
- Clean up Discord integration code and remove unused imports

### Fixed

- Add python-multipart dependency for form parsing
- Log unhandled exceptions in global error handler

## [1.2.0] - 2026-02-20

### Added

- Add average transfer rate column and detail field
- Add date range quick select to dashboard
- Add structured JSON logging with request tracking
- Add structured error handling with error codes

### Documentation

- Add error handling and structured logging specs and plans
- Add versioned changelog sections for 1.0.0 and 1.1.0

## [1.1.0] - 2026-02-19

### Added

- Add dark mode with light/dark/system theme toggle

### Documentation

- Add MIT license

## [1.0.0] - 2026-01-26

### Added

- Initial project files
- REST API for rsync log ingestion and querying
- Rsync output parser with support for all byte units
- Dashboard with HTMX-powered sync table and charts
- API key authentication
- Docker Compose development environment

### Documentation

- Add README with project documentation
- Add prerequisites and contributing sections to README
- Enhance API documentation for OpenAPI/Swagger
