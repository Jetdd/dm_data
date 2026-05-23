from __future__ import annotations

import os
from typing import Optional


class Config:
    """Unified configuration for DM and RiceQuant (rqdatac) credentials.

    Reads from environment variables (preferred) so secrets never need to
    appear in notebooks or source control.

    Required environment variables
    ------------------------------
    RQDATAC_USER        – RiceQuant username
    RQDATAC_PASSWORD    – RiceQuant password
    INNO_APP_KEY        – DM API app_key
    INNO_SM4_KEY        – DM API sm4_key

    Optional environment variables
    ------------------------------
    DM_INTRADAY_ROOT    – Local parquet root (default: E:\\dm_intraday)
    """

    def __init__(self):
        self.rqdatac_user = os.getenv("RQDATAC_USER") or os.getenv("RQDATAC_USERNAME")
        self.rqdatac_password = os.getenv("RQDATAC_PASSWORD")
        self.inno_app_key = os.getenv("INNO_APP_KEY")
        self.inno_sm4_key = os.getenv("INNO_SM4_KEY")
        self.dm_intraday_root = os.getenv("DM_INTRADAY_ROOT", r"E:\dm_intraday")

    # ---------- RiceQuant ----------

    def init_rqdatac(self, lazy: bool = True) -> None:
        """Initialize rqdatac connection using stored credentials."""
        import rqdatac

        if not self.rqdatac_user or not self.rqdatac_password:
            raise ValueError(
                "RQDATAC_USER / RQDATAC_PASSWORD not set. "
                "Set them as environment variables before calling any futures function."
            )
        rqdatac.init(self.rqdatac_user, self.rqdatac_password, lazy=lazy)

    # ---------- DM ----------

    def dm_client(self, **kwargs):
        """Return a configured DMQuantApiClient."""
        from dm_quant_api_client import DMQuantApiClient

        return DMQuantApiClient(
            app_key=self.inno_app_key,
            sm4_key=self.inno_sm4_key,
            **kwargs,
        )


# singleton
_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
