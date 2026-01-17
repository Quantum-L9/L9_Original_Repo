"""
Mac Agent Executor V2
Playwright automation engine with GUI fallback.
"""

import asyncio
import structlog
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

logger = structlog.get_logger(__name__)

from mac_agent.helpers.logging import log_step, ts

# Playwright imports
try:
    from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext,
        Page,
        TimeoutError as PlaywrightTimeoutError,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Browser automation disabled.")

# GUI fallback imports
try:
    import pyautogui
    from PIL import Image

    PYTHON_AUTOGUI_AVAILABLE = True
except ImportError:
    PYTHON_AUTOGUI_AVAILABLE = False
    logger.warning("pyautogui/Pillow not installed. GUI fallback disabled.")

from mac_agent.config import get_config
from core.decorators import must_stay_async


class AutomationExecutor:
    """Executes automation steps using Playwright (primary) or pyautogui (fallback)."""

    def __init__(self):
        self.config = get_config()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.logs: List[str] = []
        self._browser_installed = False

    @must_stay_async("callers use await")
    async def _ensure_browsers_installed(self):
        """Install Playwright browsers if not already installed."""
        if self._browser_installed:
            return

        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not available. Install with: pip install playwright && playwright install"
            )

        try:
            logger.info("Installing Playwright browsers...")
            # This will check and install if needed
            import subprocess

            result = subprocess.run(
                ["python", "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.info("Playwright browsers installed successfully")
                self._browser_installed = True
            else:
                logger.warning(f"Browser installation may have failed: {result.stderr}")
        except Exception as e:
            logger.warning(
                f"Could not auto-install browsers: {e}. Attempting to continue..."
            )
            self._browser_installed = True  # Assume browsers are installed

    async def _init_browser(self, headless: Optional[bool] = None):
        """Initialize browser context."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available")

        await self._ensure_browsers_installed()

        if self.browser is None:
            playwright = await async_playwright().start()
            # Default to visible (headless=False) unless explicitly overridden
            headless_mode = headless if headless is not None else False

            browser_type_map = {
                "chromium": playwright.chromium,
                "firefox": playwright.firefox,
                "webkit": playwright.webkit,
            }

            browser_type = browser_type_map.get(
                self.config.default_browser, playwright.chromium
            )
            self.browser = await browser_type.launch(headless=headless_mode)
            log_step(
                self.logs,
                0,
                "browser_init",
                "success",
                f"Browser launched: {self.config.default_browser} (headless={headless_mode})",
            )

        if self.context is None:
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            self.context.set_default_timeout(30000)  # 30 seconds
            log_step(self.logs, 0, "context_init", "success", "Browser context created")

        if self.page is None:
            self.page = await self.context.new_page()
            log_step(self.logs, 0, "page_init", "success", "New page created")

    async def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            self.logs.append("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def _take_screenshot(self, task_id: str, suffix: str = "") -> Optional[str]:
        """
        Take screenshot and save to task-specific directory.

        Args:
            task_id: Task ID for directory structure
            suffix: Optional suffix for filename

        Returns:
            Screenshot path or None if failed
        """
        try:
            if not self.page:
                return None

            screenshot_dir = Path(
                os.path.expanduser(f"~/.l9/mac_tasks/screenshots/{task_id}")
            )
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}{suffix}.png"
            screenshot_path = screenshot_dir / filename

            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            return str(screenshot_path)
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    async def _check_selector(self, selector: str) -> bool:
        """Check if selector exists on page."""
        try:
            if not self.page:
                return False
            element = await self.page.query_selector(selector)
            return element is not None
        except Exception:
            return False

    async def _execute_with_retry(
        self, step: Dict[str, Any], step_num: int, task_id: str, max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Execute a step with retry logic for transient failures.

        Args:
            step: Step dictionary
            step_num: Step number (1-indexed)
            task_id: Task ID for error screenshots
            max_retries: Maximum retry attempts

        Returns:
            Result dict with status and details
        """
        action = step.get("action")
        retry_count = 0

        while retry_count <= max_retries:
            try:
                if action == "goto":
                    url = step.get("url")
                    if not url:
                        raise ValueError("goto action requires 'url' parameter")
                    await self.page.goto(url, wait_until="networkidle")
                    log_step(
                        self.logs, step_num, action, "success", f"Navigated to {url}"
                    )
                    return {"status": "success", "details": f"Navigated to {url}"}

                elif action == "click":
                    selector = step.get("selector")
                    if not selector:
                        raise ValueError("click action requires 'selector' parameter")

                    # Validate selector exists
                    if not await self._check_selector(selector):
                        error_msg = f"Selector not found: {selector}"
                        log_step(self.logs, step_num, action, "error", error_msg)
                        screenshot_path = await self._take_screenshot(
                            task_id, f"_error_step{step_num}"
                        )
                        return {
                            "status": "error",
                            "details": error_msg,
                            "screenshot": screenshot_path,
                        }

                    await self.page.click(selector, timeout=10000)
                    log_step(
                        self.logs, step_num, action, "success", f"Clicked: {selector}"
                    )
                    return {"status": "success", "details": f"Clicked: {selector}"}

                elif action == "fill":
                    selector = step.get("selector")
                    text = step.get("text", "")
                    if not selector:
                        raise ValueError("fill action requires 'selector' parameter")

                    # Validate selector exists
                    if not await self._check_selector(selector):
                        error_msg = f"Selector not found: {selector}"
                        log_step(self.logs, step_num, action, "error", error_msg)
                        screenshot_path = await self._take_screenshot(
                            task_id, f"_error_step{step_num}"
                        )
                        return {
                            "status": "error",
                            "details": error_msg,
                            "screenshot": screenshot_path,
                        }

                    await self.page.fill(selector, text)
                    log_step(
                        self.logs,
                        step_num,
                        action,
                        "success",
                        f"Filled {selector} with: {text[:50]}",
                    )
                    return {"status": "success", "details": f"Filled {selector}"}

                elif action == "upload":
                    selector = step.get("selector")
                    file_path = step.get("file_path")
                    if not selector or not file_path:
                        raise ValueError(
                            "upload action requires 'selector' and 'file_path' parameters"
                        )

                    if not os.path.exists(file_path):
                        error_msg = f"File not found: {file_path}"
                        log_step(self.logs, step_num, action, "error", error_msg)
                        screenshot_path = await self._take_screenshot(
                            task_id, f"_error_step{step_num}"
                        )
                        return {
                            "status": "error",
                            "details": error_msg,
                            "screenshot": screenshot_path,
                        }

                    # Validate selector exists
                    if not await self._check_selector(selector):
                        error_msg = f"Selector not found: {selector}"
                        log_step(self.logs, step_num, action, "error", error_msg)
                        screenshot_path = await self._take_screenshot(
                            task_id, f"_error_step{step_num}"
                        )
                        return {
                            "status": "error",
                            "details": error_msg,
                            "screenshot": screenshot_path,
                        }

                    await self.page.set_input_files(selector, file_path)
                    log_step(
                        self.logs,
                        step_num,
                        action,
                        "success",
                        f"Uploaded file: {os.path.basename(file_path)}",
                    )
                    return {
                        "status": "success",
                        "details": f"Uploaded: {os.path.basename(file_path)}",
                    }

                elif action == "wait_for" or action == "wait":
                    selector = step.get("selector")
                    timeout = step.get("timeout", 10000)
                    if not selector:
                        raise ValueError("wait action requires 'selector' parameter")
                    await self.page.wait_for_selector(selector, timeout=timeout)
                    log_step(
                        self.logs,
                        step_num,
                        action,
                        "success",
                        f"Waited for: {selector}",
                    )
                    return {"status": "success", "details": f"Waited for: {selector}"}

                elif action == "scroll":
                    direction = step.get("direction", "down")
                    pixels = step.get("pixels", 500)
                    if direction == "down":
                        await self.page.evaluate(f"window.scrollBy(0, {pixels})")
                    elif direction == "up":
                        await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
                    log_step(
                        self.logs,
                        step_num,
                        action,
                        "success",
                        f"Scrolled {direction} {pixels}px",
                    )
                    return {"status": "success", "details": f"Scrolled {direction}"}

                elif action == "screenshot":
                    screenshot_path = await self._take_screenshot(
                        task_id, f"_step{step_num}"
                    )
                    if screenshot_path:
                        log_step(
                            self.logs,
                            step_num,
                            action,
                            "success",
                            f"Screenshot: {screenshot_path}",
                        )
                        return {
                            "status": "success",
                            "details": screenshot_path,
                            "screenshot": screenshot_path,
                        }
                    else:
                        log_step(
                            self.logs,
                            step_num,
                            action,
                            "error",
                            "Failed to take screenshot",
                        )
                        return {
                            "status": "error",
                            "details": "Failed to take screenshot",
                        }

                else:
                    raise ValueError(f"Unknown action: {action}")

            except (PlaywrightTimeoutError, Exception) as e:
                error_str = str(e)
                error_type = type(e).__name__

                # Check if this is a retryable error
                is_retryable = (
                    isinstance(e, PlaywrightTimeoutError)
                    or "net::ERR_FAILED" in error_str
                    or "ElementHandleError" in error_type
                    or "TimeoutError" in error_type
                )

                if is_retryable and retry_count < max_retries:
                    retry_count += 1
                    backoff = 0.5 * (2 ** (retry_count - 1))  # Exponential: 0.5s, 1s
                    log_step(
                        self.logs,
                        step_num,
                        action,
                        "retry",
                        f"Attempt {retry_count}/{max_retries}: {error_str}",
                    )
                    await asyncio.sleep(backoff)
                    continue
                else:
                    # Not retryable or max retries reached
                    log_step(
                        self.logs,
                        step_num,
                        action,
                        "error",
                        f"{error_type}: {error_str}",
                    )
                    screenshot_path = await self._take_screenshot(
                        task_id, f"_error_step{step_num}"
                    )
                    return {
                        "status": "error",
                        "details": f"{error_type}: {error_str}",
                        "screenshot": screenshot_path,
                    }

        # Should never reach here, but just in case
        log_step(self.logs, step_num, action, "error", "Max retries exceeded")
        screenshot_path = await self._take_screenshot(task_id, f"_error_step{step_num}")
        return {
            "status": "error",
            "details": "Max retries exceeded",
            "screenshot": screenshot_path,
        }

    async def run_steps(
        self,
        steps: List[Dict[str, Any]],
        headless: Optional[bool] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute automation steps with structured logging, retries, and error handling.

        Args:
            steps: List of step dictionaries with 'action' and parameters
            headless: Override headless setting (defaults to False - visible browser)
            task_id: Task ID for screenshot organization

        Returns:
            {
                "status": "success" | "error",
                "logs": [structured log entries],
                "screenshots": [list of screenshot paths],
                "started_at": ISO timestamp,
                "finished_at": ISO timestamp,
                "data": {...}
            }
        """
        self.logs = []
        screenshots = []
        started_at = ts()
        overall_status = "success"

        # Use task_id or generate one
        if not task_id:
            task_id = f"task_{int(time.time())}"

        try:
            # Initialize browser (default to visible unless explicitly headless)
            await self._init_browser(headless)

            # Execute each step with error handling
            for i, step in enumerate(steps, 1):
                try:
                    result = await self._execute_with_retry(step, i, task_id)

                    # Collect screenshot if step produced one
                    if result.get("screenshot"):
                        screenshots.append(result["screenshot"])

                    # If step failed, mark overall status and take final screenshot
                    if result["status"] == "error":
                        overall_status = "error"
                        # Take error screenshot if not already taken
                        if not screenshots:
                            error_screenshot = await self._take_screenshot(
                                task_id, "_final_error"
                            )
                            if error_screenshot:
                                screenshots.append(error_screenshot)
                        break  # Stop execution on error

                except Exception as e:
                    # Unexpected error in step execution wrapper
                    error_msg = f"Step {i} execution error: {str(e)}"
                    log_step(
                        self.logs, i, step.get("action", "unknown"), "error", error_msg
                    )
                    logger.error(error_msg, exc_info=True)
                    overall_status = "error"
                    error_screenshot = await self._take_screenshot(
                        task_id, f"_error_step{i}"
                    )
                    if error_screenshot:
                        screenshots.append(error_screenshot)
                    break

            # Take final success screenshot if no errors
            if overall_status == "success" and not screenshots:
                final_screenshot = await self._take_screenshot(task_id, "_final")
                if final_screenshot:
                    screenshots.append(final_screenshot)

            # Get page data if available
            page_data = {}
            try:
                if self.page:
                    page_data = {"url": self.page.url, "title": await self.page.title()}
            except Exception:
                pass

            finished_at = ts()

            return {
                "status": overall_status,
                "logs": self.logs,
                "screenshots": screenshots,
                "screenshot_path": screenshots[0]
                if screenshots
                else None,  # Backward compatibility
                "started_at": started_at,
                "finished_at": finished_at,
                "data": page_data,
            }

        except Exception as e:
            # Catastrophic error
            error_msg = f"Execution error: {str(e)}"
            log_step(self.logs, 0, "execution", "error", error_msg)
            logger.error(error_msg, exc_info=True)

            # Try to take error screenshot
            error_screenshot = await self._take_screenshot(
                task_id, "_catastrophic_error"
            )
            if error_screenshot:
                screenshots.append(error_screenshot)

            finished_at = ts()

            return {
                "status": "error",
                "logs": self.logs,
                "screenshots": screenshots,
                "screenshot_path": screenshots[0] if screenshots else None,
                "started_at": started_at,
                "finished_at": finished_at,
                "data": {"error": error_msg},
            }

        finally:
            # Cleanup
            await self._cleanup()

    def run_gui_fallback(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute steps using pyautogui fallback (for non-browser automation).

        Args:
            steps: List of step dictionaries

        Returns:
            Result dictionary
        """
        if not PYTHON_AUTOGUI_AVAILABLE:
            raise RuntimeError(
                "pyautogui not available. Install with: pip install pyautogui Pillow"
            )

        self.logs = []
        screenshot_path = None

        try:
            for i, step in enumerate(steps):
                action = step.get("action")
                self.logs.append(f"GUI Step {i + 1}: {action}")

                if action == "click":
                    x = step.get("x")
                    y = step.get("y")
                    if x is not None and y is not None:
                        pyautogui.click(x, y)
                        self.logs.append(f"Clicked at ({x}, {y})")
                    else:
                        raise ValueError("GUI click requires 'x' and 'y' parameters")

                elif action == "type":
                    text = step.get("text", "")
                    pyautogui.write(text, interval=0.1)
                    self.logs.append(f"Typed: {text[:50]}")

                elif action == "screenshot":
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(
                        self.config.screenshot_dir, f"gui_screenshot_{timestamp}.png"
                    )
                    screenshot = pyautogui.screenshot()
                    screenshot.save(screenshot_path)
                    self.logs.append(f"Screenshot saved: {screenshot_path}")

                else:
                    raise ValueError(f"Unknown GUI action: {action}")

            if screenshot_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(
                    self.config.screenshot_dir, f"gui_screenshot_{timestamp}.png"
                )
                screenshot = pyautogui.screenshot()
                screenshot.save(screenshot_path)
                self.logs.append(f"Final screenshot saved: {screenshot_path}")

            return {
                "status": "success",
                "logs": self.logs,
                "screenshot_path": screenshot_path,
                "data": {},
            }

        except Exception as e:
            error_msg = f"GUI execution error: {str(e)}"
            self.logs.append(f"ERROR: {error_msg}")
            logger.error(error_msg, exc_info=True)

            return {
                "status": "error",
                "logs": self.logs,
                "screenshot_path": screenshot_path,
                "data": {"error": error_msg},
            }
