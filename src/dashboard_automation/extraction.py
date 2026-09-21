from __future__ import annotations

from typing import Protocol

import pandas as pd
from databricks import sql

from .config import QueryConfig


class QueryExecutor(Protocol):
    def execute(self, query: QueryConfig) -> pd.DataFrame: ...


class DatabricksSQLExecutor:
    def __init__(
        self,
        server_hostname: str,
        http_path_by_warehouse: dict[str, str],
        access_token: str,
    ) -> None:
        self._server_hostname = server_hostname
        self._http_path_by_warehouse = http_path_by_warehouse
        self._access_token = access_token

    def execute(self, query: QueryConfig) -> pd.DataFrame:
        try:
            http_path = self._http_path_by_warehouse[query.warehouse]
        except KeyError:
            raise KeyError(
                f"warehouse {query.warehouse!r} não configurado "
                f"(configurados: {sorted(self._http_path_by_warehouse)})"
            ) from None
        with sql.connect(
            server_hostname=self._server_hostname,
            http_path=http_path,
            access_token=self._access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query.sql)
                return cursor.fetchall_arrow().to_pandas()
