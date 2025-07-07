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
        for tries in range(1, 1 + max_tries):
            resp = super().request(method, url, *args, **kwargs)
            if expected(resp):
                break
            time.sleep(delay_unexpected)
            self.auth_request() # Call the new auth_request
        else:
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
