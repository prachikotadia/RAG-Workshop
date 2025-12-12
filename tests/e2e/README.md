# E2E Tests with Playwright

## Setup

1. Install Playwright:
```bash
npm install -D @playwright/test
npx playwright install
```

2. Install Python test dependencies:
```bash
pip install pytest pytest-playwright
```

## Running E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/

# Run with UI mode
pytest tests/e2e/ --headed

# Run specific test
pytest tests/e2e/test_auth_flow.py
```

## Test Structure

- `test_auth_flow.py` - Authentication and user management
- `test_document_upload.py` - Document upload and management
- `test_chat_flow.py` - Chat functionality and RAG
- `test_analytics.py` - Analytics dashboard

## CI Integration

E2E tests run in CI with:
- Backend server started in background
- Frontend server started in background
- Tests run against both servers
- Cleanup after tests complete

