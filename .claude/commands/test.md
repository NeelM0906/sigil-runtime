Run the project test suite and report results.

Steps:
1. Run: `PYTHONPATH=src python3 -m pytest tests/ -v --tb=short 2>&1 | tail -80`
2. If all tests pass, report the count and exit
3. If any tests fail:
   - List each failing test with its error summary
   - Read the failing test file to understand what it expects
   - Read the source file being tested
   - Suggest a fix with the specific file and line number
4. If asked to run a specific test file, use: `PYTHONPATH=src python3 -m pytest <file> -v -s`

Do NOT modify any code unless explicitly asked. This command is read-only by default.
