# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- Implement webhook notification service
- Add failure detection with exit code tracking and stale sync monitoring

### Changed

- Fix lint warnings in webhook dispatcher tests

### Documentation

- Add webhook service spec and update M2 milestone progress
- Update changelog for v1.2.0 and complete M1 cycle

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
