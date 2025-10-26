# DeepKeep

## 1. Running Tests
To run the tests with generating html report, execute the following command from root directory:

```bash
pytest --html=test_results/report.html
```

## 2. Activation Mode

To toggle the activation mode, set the `ACTIVATION_MODE` value in `constants.py` to one of the following:

- `'immediate'` – the activation happens instantly  
- `'eventual'` – the activation happens after delay specified in ACTIVATION_DELAY_S from constants.py

## 3. CI

1. Autoruns are set on GitHub Actions for each push event. Workflow is described here:
https://github.com/ivaniukihornik/DeepKeep/blob/test_task/.github/workflows/autotests.yml

2. You may watch the results by the link:
https://github.com/ivaniukihornik/DeepKeep/actions

3. Test artifacts (html report and api logs) can be uploaded from inside test run as specified on screenshot https://ibb.co/fG2jc16z

## 4. Comments

1. Requests + ThreadPoolExecutor were used to run multiple simple requests concurrently, providing I/O-bound "parallelism" without introducing the complexity of async code
2. Basis Endpoint Object Model autotests pattern was used for effective API client methods reusing
3. Frequently used helpers were described as fixtures
4. Helpers with general logic were described in separate file helpers.py
5. For resetting server state after each test additional mock endpoint was created 