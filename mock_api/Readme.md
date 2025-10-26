# Mock Server Overview

## 1. Why FastAPI
The mock server was created using **FastAPI** because this framework allows:

- Implementing complex API logic
- Running the server in **asynchronous mode**, which is important for testing API behaviour under concurrency
- Implementing simple payload fields validation with pydantic models

## 2. How to Run the Mock Server
To start the mock server, execute from project root dir:

```bash
uvicorn mock_api.app:app
```

By default, it listens on http://127.0.0.1:8000.
You can also specify a custom port using the --port option:

```bash
uvicorn mock_api.app:app --port 5000
```

**Important:** Make sure the MOCK_SERVER_PORT value in constants.py matches the port you are using.

## 3. How to read API logs
To read API logs see the console or open api.log file in test_results/ directory. It generates automatically after server stopping