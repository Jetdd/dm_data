from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class Config:
    """Unified configuration for DM and RiceQuant (rqdatac) credentials.

    Values are resolved in this order:
    1. Manually passed to ``Config(...)``.
    2. Environment variables.
    3. Hard-coded defaults.

    Environment variables
    ---------------------
    RQDATAC_USER / RQDATAC_USERNAME – RiceQuant username
    RQDATAC_PASSWORD                – RiceQuant password
    INNO_APP_KEY                    – DM API app_key
    INNO_SM4_KEY                    – DM API sm4_key
    DM_INTRADAY_ROOT                – Local parquet root (default: E:\\dm_intraday)
    """

    def __init__(
        self,
        *,
        rqdatac_user: str | None = None,
        rqdatac_password: str | None = None,
        inno_app_key: str | None = None,
        inno_sm4_key: str | None = None,
        root: str | os.PathLike[str] | None = None,
    ):
        self.rqdatac_user = (
            rqdatac_user
            or os.getenv("RQDATAC_USER")
            or os.getenv("RQDATAC_USERNAME")
        )
        self.rqdatac_password = (
            rqdatac_password or os.getenv("RQDATAC_PASSWORD")
        )
        self.inno_app_key = inno_app_key or os.getenv("INNO_APP_KEY")
        self.inno_sm4_key = inno_sm4_key or os.getenv("INNO_SM4_KEY")
        self.dm_intraday_root = (
            Path(root)
            if root is not None
            else Path(os.getenv("DM_INTRADAY_ROOT", r"E:\dm_intraday"))
        )

    # ---------- RiceQuant ----------

    def init_rqdatac(self, lazy: bool = True) -> None:
        """Initialize rqdatac connection using stored credentials."""
        import rqdatac

        if not self.rqdatac_user or not self.rqdatac_password:
            raise ValueError(
                "RQDATAC_USER / RQDATAC_PASSWORD not set. "
                "Pass them to Config(...) or set as environment variables."
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


def get_config(
    *,
    rqdatac_user: str | None = None,
    rqdatac_password: str | None = None,
    inno_app_key: str | None = None,
    inno_sm4_key: str | None = None,
    root: str | os.PathLike[str] | None = None,
) -> Config:
    """Return the global Config singleton.

    If any argument is passed, a **new** ``Config`` instance is created
    (and cached) so that subsequent calls return the overridden values.
    """
    global _config
    if _config is None or any(
        v is not None
        for v in (rqdatac_user, rqdatac_password, inno_app_key, inno_sm4_key, root)
    ):
        _config = Config(
            rqdatac_user=rqdatac_user,
            rqdatac_password=rqdatac_password,
            inno_app_key=inno_app_key,
            inno_sm4_key=inno_sm4_key,
            root=root,
        )
    return _config
