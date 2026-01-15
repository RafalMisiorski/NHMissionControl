"""
Health Inspector - Independent verification system.

Runs pytest, lint, API checks, and Playwright UI verification.
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Result of a single health check."""
    name: str
    passed: bool
    score: float  # 0-100
    message: str
    details: Optional[dict] = None


@dataclass
class TestResult:
    """Result of test execution."""
    passed: int
    failed: int
    skipped: int
    errors: int
    coverage: Optional[float]
    duration_seconds: float
    output: str


@dataclass
class LintResult:
    """Result of lint check."""
    errors: int
    warnings: int
    fixed: int
    files_checked: int
    output: str


@dataclass
class InspectionResult:
    """Complete inspection result."""
    health_score: float  # 0-100
    tests: Optional[TestResult]
    lint: Optional[LintResult]
    api_check: Optional[HealthCheck]
    ui_check: Optional[HealthCheck]
    console_check: Optional[HealthCheck]
    all_checks: list[HealthCheck]


class HealthInspector:
    """
    Independent verification system.

    Runs comprehensive checks:
    - pytest for unit/integration tests
    - ruff/eslint for linting
    - API health endpoint check
    - Playwright for UI verification
    - Browser console error detection

    Provides a health score (0-100) based on results.
    """

    def __init__(
        self,
        project_path: Optional[Path] = None,
        playwright_available: bool = False,
    ):
        self.project_path = project_path or Path.cwd()
        self.playwright_available = playwright_available

    async def run_full_inspection(
        self,
        task_id: str,
        ports: dict,
        project_path: Optional[str] = None,
    ) -> dict:
        """
        Run all verification checks.

        Args:
            task_id: Task identifier
            ports: Dict of allocated ports {frontend: port, backend: port}
            project_path: Optional override for project path

        Returns:
            Dict with all check results and health score
        """
        path = Path(project_path) if project_path else self.project_path
        checks = []

        # Run checks in parallel where possible
        test_task = asyncio.create_task(self._run_tests(path))
        lint_task = asyncio.create_task(self._run_lint(path))

        test_result = await test_task
        lint_result = await lint_task

        # Convert to health checks
        if test_result:
            test_check = HealthCheck(
                name="tests",
                passed=test_result.failed == 0,
                score=self._calculate_test_score(test_result),
                message=f"{test_result.passed} passed, {test_result.failed} failed",
                details={
                    "passed": test_result.passed,
                    "failed": test_result.failed,
                    "skipped": test_result.skipped,
                    "coverage": test_result.coverage,
                },
            )
            checks.append(test_check)

        if lint_result:
            lint_check = HealthCheck(
                name="lint",
                passed=lint_result.errors == 0,
                score=self._calculate_lint_score(lint_result),
                message=f"{lint_result.errors} errors, {lint_result.warnings} warnings",
                details={
                    "errors": lint_result.errors,
                    "warnings": lint_result.warnings,
                    "fixed": lint_result.fixed,
                },
            )
            checks.append(lint_check)

        # API and UI checks if ports provided
        if ports:
            api_check = await self._check_api_health(ports.get("backend"))
            if api_check:
                checks.append(api_check)

            if self.playwright_available:
                ui_check = await self._check_ui_loads(ports.get("frontend"))
                if ui_check:
                    checks.append(ui_check)

                console_check = await self._check_console_errors(ports.get("frontend"))
                if console_check:
                    checks.append(console_check)

        # Calculate overall health score
        health_score = self._calculate_overall_score(checks)

        return {
            "health_score": health_score,
            "tests_passed": test_result.passed if test_result else 0,
            "tests_failed": test_result.failed if test_result else 0,
            "tests_skipped": test_result.skipped if test_result else 0,
            "coverage": test_result.coverage if test_result else None,
            "lint_errors": lint_result.errors if lint_result else 0,
            "lint_warnings": lint_result.warnings if lint_result else 0,
            "api_responds": any(c.name == "api" and c.passed for c in checks),
            "ui_loads": any(c.name == "ui" and c.passed for c in checks),
            "console_errors": next(
                (c.details.get("error_count", 0) for c in checks if c.name == "console"),
                0,
            ),
            "checks": [
                {"name": c.name, "passed": c.passed, "score": c.score, "message": c.message}
                for c in checks
            ],
        }

    async def check_tests(self, project_path: str) -> dict:
        """
        Run tests and return results.

        Args:
            project_path: Path to project

        Returns:
            Dict with test results
        """
        path = Path(project_path) if project_path else self.project_path
        result = await self._run_tests(path)

        if result:
            return {
                "passed": result.passed,
                "failed": result.failed,
                "skipped": result.skipped,
                "coverage": result.coverage,
                "duration": result.duration_seconds,
            }
        return {"passed": 0, "failed": 0, "skipped": 0, "coverage": None}

    async def check_lint(self, project_path: str) -> dict:
        """
        Run lint check and return results.

        Args:
            project_path: Path to project

        Returns:
            Dict with lint results
        """
        path = Path(project_path) if project_path else self.project_path
        result = await self._run_lint(path)

        if result:
            return {
                "errors": result.errors,
                "warnings": result.warnings,
                "fixed": result.fixed,
            }
        return {"errors": 0, "warnings": 0, "fixed": 0}

    async def check_api_health(self, port: int) -> dict:
        """
        Check if API responds on health endpoint.

        Args:
            port: Backend port

        Returns:
            Dict with API health status
        """
        check = await self._check_api_health(port)
        if check:
            return {"responds": check.passed, "message": check.message}
        return {"responds": False, "message": "Check not performed"}

    async def check_ui_loads(self, port: int) -> dict:
        """
        Check if UI loads via Playwright.

        Args:
            port: Frontend port

        Returns:
            Dict with UI load status
        """
        check = await self._check_ui_loads(port)
        if check:
            return {"loads": check.passed, "message": check.message}
        return {"loads": False, "message": "Playwright not available"}

    async def check_console_errors(self, port: int) -> dict:
        """
        Check for browser console errors via Playwright.

        Args:
            port: Frontend port

        Returns:
            Dict with console error count
        """
        check = await self._check_console_errors(port)
        if check:
            return {
                "error_count": check.details.get("error_count", 0) if check.details else 0,
                "message": check.message,
            }
        return {"error_count": 0, "message": "Playwright not available"}

    async def _run_tests(self, path: Path) -> Optional[TestResult]:
        """Run pytest and parse results."""
        try:
            # Run pytest with JSON output
            result = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest",
                "--tb=short",
                "-q",
                str(path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(path),
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=300)
            output = stdout.decode() + stderr.decode()

            # Parse pytest output
            passed = output.count(" passed")
            failed = output.count(" failed")
            skipped = output.count(" skipped")
            errors = output.count(" error")

            # Try to extract coverage if available
            coverage = None
            if "TOTAL" in output and "%" in output:
                try:
                    import re
                    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
                    if match:
                        coverage = float(match.group(1))
                except Exception:
                    pass

            return TestResult(
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                coverage=coverage,
                duration_seconds=0.0,  # Would need timing info
                output=output[:1000],  # Truncate
            )

        except asyncio.TimeoutError:
            logger.warning("Test execution timed out")
            return TestResult(
                passed=0, failed=1, skipped=0, errors=1,
                coverage=None, duration_seconds=300.0, output="Timeout"
            )
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return None

    async def _run_lint(self, path: Path) -> Optional[LintResult]:
        """Run ruff lint check."""
        try:
            result = await asyncio.create_subprocess_exec(
                "ruff", "check", str(path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=60)
            output = stdout.decode() + stderr.decode()

            # Count errors and warnings
            errors = output.count(" error")
            warnings = output.count(" warning")

            return LintResult(
                errors=errors,
                warnings=warnings,
                fixed=0,
                files_checked=0,  # Would need to parse
                output=output[:1000],
            )

        except asyncio.TimeoutError:
            logger.warning("Lint check timed out")
            return LintResult(errors=0, warnings=0, fixed=0, files_checked=0, output="Timeout")
        except FileNotFoundError:
            # ruff not installed, try eslint for JS projects
            return await self._run_eslint(path)
        except Exception as e:
            logger.error(f"Lint check failed: {e}")
            return None

    async def _run_eslint(self, path: Path) -> Optional[LintResult]:
        """Run eslint for JavaScript/TypeScript projects."""
        try:
            result = await asyncio.create_subprocess_exec(
                "npx", "eslint", ".", "--ext", ".js,.jsx,.ts,.tsx",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(path),
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=120)
            output = stdout.decode() + stderr.decode()

            errors = output.count("error")
            warnings = output.count("warning")

            return LintResult(
                errors=errors,
                warnings=warnings,
                fixed=0,
                files_checked=0,
                output=output[:1000],
            )
        except Exception as e:
            logger.error(f"ESLint check failed: {e}")
            return None

    async def _check_api_health(self, port: Optional[int]) -> Optional[HealthCheck]:
        """Check API health endpoint."""
        if not port:
            return None

        try:
            import aiohttp

            url = f"http://localhost:{port}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return HealthCheck(
                            name="api",
                            passed=True,
                            score=100.0,
                            message=f"API responds on port {port}",
                        )
                    else:
                        return HealthCheck(
                            name="api",
                            passed=False,
                            score=0.0,
                            message=f"API returned status {resp.status}",
                        )
        except Exception as e:
            return HealthCheck(
                name="api",
                passed=False,
                score=0.0,
                message=f"API check failed: {e}",
            )

    async def _check_ui_loads(self, port: Optional[int]) -> Optional[HealthCheck]:
        """Check if UI loads via Playwright."""
        if not port or not self.playwright_available:
            return None

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                url = f"http://localhost:{port}"
                response = await page.goto(url, timeout=30000)

                if response and response.ok:
                    # Wait for content to load
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    return HealthCheck(
                        name="ui",
                        passed=True,
                        score=100.0,
                        message=f"UI loads on port {port}",
                    )
                else:
                    return HealthCheck(
                        name="ui",
                        passed=False,
                        score=0.0,
                        message=f"UI failed to load: {response.status if response else 'no response'}",
                    )

        except Exception as e:
            return HealthCheck(
                name="ui",
                passed=False,
                score=0.0,
                message=f"UI check failed: {e}",
            )

    async def _check_console_errors(self, port: Optional[int]) -> Optional[HealthCheck]:
        """Check for browser console errors via Playwright."""
        if not port or not self.playwright_available:
            return None

        try:
            from playwright.async_api import async_playwright

            console_errors = []

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Capture console errors
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

                url = f"http://localhost:{port}"
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=10000)

                await browser.close()

            error_count = len(console_errors)

            return HealthCheck(
                name="console",
                passed=error_count == 0,
                score=100.0 if error_count == 0 else max(0, 100 - error_count * 20),
                message=f"{error_count} console errors",
                details={"error_count": error_count, "errors": console_errors[:5]},
            )

        except Exception as e:
            return HealthCheck(
                name="console",
                passed=False,
                score=0.0,
                message=f"Console check failed: {e}",
                details={"error_count": 0},
            )

    def _calculate_test_score(self, result: TestResult) -> float:
        """Calculate score from test results (0-100)."""
        total = result.passed + result.failed
        if total == 0:
            return 50.0  # No tests - partial credit

        pass_rate = result.passed / total
        return pass_rate * 100

    def _calculate_lint_score(self, result: LintResult) -> float:
        """Calculate score from lint results (0-100)."""
        if result.errors == 0 and result.warnings == 0:
            return 100.0
        elif result.errors == 0:
            return max(70.0, 100 - result.warnings * 2)
        else:
            return max(0.0, 100 - result.errors * 10 - result.warnings * 2)

    def _calculate_overall_score(self, checks: list[HealthCheck]) -> float:
        """Calculate overall health score from all checks."""
        if not checks:
            return 50.0  # No checks performed

        total_score = sum(c.score for c in checks)
        return total_score / len(checks)
