import os
import logging
from time import sleep
import requests

__all__ = ['ApiClient']

logger = logging.getLogger(__name__)

class ApiClient:
    """
    API 客户端，负责登录获取 cookie 并管理 session。

    Attributes:
        domain (str): API 服务域名
        api_key (str): 用于认证的 API Key
        cookie (Optional[str]): 存储当前有效的 cookie
    """
    
    def __init__(self):
        self.domain = os.getenv('API_DOMAIN')
        self.api_key = os.getenv('API_KEY')
        self.cookie = None

    def _request_cookie(self, old_cookie: str = None, force_update: bool = False) -> str:
        """
        向登录接口请求新的 cookie，最多重试 3 次。

        Args:
            old_cookie (str, optional): 上一次获取的 cookie
            force_update (bool): 是否强制刷新

        Returns:
            str: 登录获取的 cookie，如果失败返回 None
        """
        url = f'{self.domain}/login'
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"cookie": old_cookie, "force_update": force_update}

        for attempt in range(1, 4):
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Login response: {data}")
                return data.get('cookie')
            except Exception as e:
                logger.warning(f"登录尝试 第 {attempt} 次失败: {e}")
                sleep(10 * attempt)
        logger.error("登录重试 3 次后失败，未获取到 cookie。")
        return None

    def login(self, force_update: bool = False) -> requests.Session:
        """
        登录并获取新的 cookie，然后构造带有 cookie 的 session。

        Args:
            force_update (bool): 是否强制刷新 cookie

        Returns:
            requests.Session: 带有最新 cookie 的 session 对象
        """
        # 获取或刷新 cookie
        self.cookie = self._request_cookie(old_cookie=self.cookie, force_update=force_update)
        # 构建 session
        session = requests.Session()
        if self.cookie:
            session.headers.update({"Cookie": self.cookie})
        return session

    def get_session(self, force_update=False) -> requests.Session:
        """
        获取带有有效 cookie 的 session，如果尚未登录则先执行登录流程。

        Returns:
            requests.Session: 带有有效 cookie 的 session 对象
        """
        if not self.cookie:
            # 首次获取默认使用非强制刷新
            return self.login(force_update=force_update)
        session = requests.Session()
        session.headers.update({"Cookie": self.cookie})
        return session