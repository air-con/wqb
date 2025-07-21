import logging
import time
from collections.abc import Callable
from requests import Response, Session
from .session import ApiClient

__all__ = ['AutoAuthSession']
logger = logging.getLogger(__name__)

class AutoAuthSession(Session):

    def __init__(
        self,
        api_client: ApiClient,
        *,
        expected: Callable[[Response], bool] = lambda _: True,
        max_tries: int = 3,
        delay_unexpected: float = 2.0,
        logger: logging.Logger = logger,
        **kwargs,
    ) -> None:
        super().__init__()
        self.api_client = api_client
        self.expected = expected
        self.max_tries = max(1, max_tries)
        self.delay_unexpected = max(0.0, delay_unexpected)
        self.logger = logger
        self.kwargs = kwargs
        self.auth_inited = False

    def __repr__(
        self,
    ) -> str:
        """
        Returns a string representation of the `AutoAuthSession` object.

        Returns
        -------
        str
            A string representation of the `AutoAuthSession` object.
        """
        return f"<AutoAuthSession []>"

    def auth_request(
        self,
        log: str | None = None,
    ) -> Response:
        """
        Logs in using the ApiClient and updates the session headers.
        """
        if log is not None:
            self.logger.info(f"start login from auto_auth_session: self.api_client.cookie")
        new_session = self.api_client.login(force_update=False)
        self.headers.update(new_session.headers)
        if log is not None:
            self.logger.info(f"{self}.auth_request(...): {log}")
        # Since this method no longer returns a Response, we can return None
        # or a custom success indicator if needed. For now, we'll adjust the
        # request method to handle this.
        return None

    def request(
        self,
        method: str,
        url: str,
        *args,
        expected: Callable[[Response], bool] | None = None,
        max_tries: int | None = None,
        delay_unexpected: float | None = None,
        log: str | None = None,
        **kwargs,
    ) -> Response:
        if expected is None:
            expected = self.expected
        if max_tries is None:
            max_tries = self.max_tries
        if delay_unexpected is None:
            delay_unexpected = self.delay_unexpected
        max_tries = max(1, max_tries)
        delay_unexpected = max(0.0, delay_unexpected)
        if not self.auth_inited:
            self.auth_inited = True
            self.auth_request()

        for tries in range(1, 1 + max_tries):
            resp = super().request(method, url, *args, **kwargs)
            if expected(resp):
                break # Success, exit the loop

            self.logger.warning(f"{self}.request(...) [{tries} tries]: {resp.status_code} {resp.reason} {resp.text} {resp.elapsed} {resp.headers}")

            # --- Start of the final, focused error handling logic ---

            # Special exception for 400 Bad Request: abort immediately.
            if resp.status_code == 400:
                self.logger.error(f"Received 400 Bad Request. This is a non-retryable client error. Aborting.")
                break

            # For all other errors, use the original retry/re-login logic.
            is_simulation_limit = False
            try:
                response_json = resp.json()
                if isinstance(response_json, dict):
                    if 'SIMULATION_LIMIT_EXCEEDED' in response_json.get('detail', ''):
                        is_simulation_limit = True
            except ValueError:
                pass # Not a JSON response

            if resp.status_code == 504:
                self.logger.warning(f"Received 504 Gateway Timeout. Retrying in {delay_unexpected} seconds...")
                time.sleep(delay_unexpected)
            elif is_simulation_limit: # This is a specific type of 429 error
                self.logger.warning(f"Simulation limit exceeded. Retrying in {10 * delay_unexpected} seconds...")
                time.sleep(10 * delay_unexpected)
            else:
                self.logger.warning("Attempting to recover from error by re-authenticating.")
                time.sleep(delay_unexpected)
                self.auth_request() # Re-authenticate for other errors (e.g., 401, 403, 5xx)

            # --- End of the final logic ---

        else: # This block now only runs if the loop completes without a `break`
            self.logger.warning(
                '\n'.join(
                    (
                        f"{self}.request(...) [max {tries} tries ran out]",
                        f"super().request(method, url, *args, **kwargs):",
                        f"    method: {method}",
                        f"    url: {url}",
                        f"    args: {args}",
                        f"    kwargs: {kwargs}",
                        f"{resp}:",
                        f"    status_code: {resp.status_code}",
                        f"    reason: {resp.reason}",
                        f"    url: {resp.url}",
                        f"    elapsed: {resp.elapsed}",
                        f"    headers: {resp.headers}",
                        f"    text: {resp.text}",
                    )
                )
            )
        if log is not None:
            self.logger.info(f"{self}.request(...) [{tries} tries]: {log}")
        return resp
