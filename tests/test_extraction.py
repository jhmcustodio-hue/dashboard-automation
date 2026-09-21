from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dashboard_automation.config import QueryConfig
from dashboard_automation.extraction import DatabricksSQLExecutor


def test_execute_runs_query_on_correct_warehouse_and_returns_dataframe():
    expected_df = pd.DataFrame({"a": [1, 2]})

    mock_cursor = MagicMock()
    mock_cursor.fetchall_arrow.return_value.to_pandas.return_value = expected_df
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.__exit__.return_value = False

    with patch(
        "dashboard_automation.extraction.sql.connect", return_value=mock_connection
    ) as mock_connect:
        executor = DatabricksSQLExecutor(
            server_hostname="adb-123.azuredatabricks.net",
            http_path_by_warehouse={"meu-warehouse": "/sql/1.0/warehouses/abc123"},
            access_token="fake-token",
        )
        result = executor.execute(QueryConfig(sql="SELECT 1", warehouse="meu-warehouse"))

    mock_connect.assert_called_once_with(
        server_hostname="adb-123.azuredatabricks.net",
        http_path="/sql/1.0/warehouses/abc123",
        access_token="fake-token",
    )
    mock_cursor.execute.assert_called_once_with("SELECT 1")
    pd.testing.assert_frame_equal(result, expected_df)


def test_execute_raises_actionable_error_for_unknown_warehouse():
    executor = DatabricksSQLExecutor(
        server_hostname="adb-123.azuredatabricks.net",
        http_path_by_warehouse={"meu-warehouse": "/sql/1.0/warehouses/abc123"},
        access_token="fake-token",
    )

    with pytest.raises(KeyError) as exc_info:
        executor.execute(QueryConfig(sql="SELECT 1", warehouse="warehouse-de-vendas"))

    message = str(exc_info.value)
    assert "warehouse-de-vendas" in message
    assert "meu-warehouse" in message
