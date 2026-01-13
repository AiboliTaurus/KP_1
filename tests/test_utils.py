"""
Тесты для модуля utils.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# Добавляем src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.utils import (
    filter_transactions_by_date,
    get_time_greeting,
    handle_exception,
    load_transactions_from_excel,
    load_user_settings,
)


class TestHandleException:
    """Тесты для декоратора handle_exception"""

    def test_handle_exception_success(self):
        """Тест успешного выполнения функции"""

        @handle_exception
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_handle_exception_failure(self, caplog):
        """Тест обработки исключения"""
        # Настраиваем логирование
        import logging
        logging.basicConfig(level=logging.ERROR)

        @handle_exception
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc_info:
            failing_function()

        assert "Test error" in str(exc_info.value)

    def test_handle_exception_with_args(self):
        """Тест функции с аргументами"""

        @handle_exception
        def multiply(x, y):
            return x * y

        result = multiply(5, 6)
        assert result == 30

    def test_handle_exception_with_kwargs(self):
        """Тест функции с ключевыми аргументами"""

        @handle_exception
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = greet("World", greeting="Привет")
        assert result == "Привет, World!"


class TestLoadTransactionsFromExcel:
    """Тесты для функции load_transactions_from_excel"""

    def test_load_transactions_success(self, mock_excel_file, mock_os_path):
        """Тест успешной загрузки транзакций"""
        with patch('src.utils.pd.read_excel') as mock_read:
            # Создаем полный DataFrame со всеми обязательными столбцами
            data = {
                'Дата операции': pd.date_range('2024-01-01', periods=3),
                'Дата платежа': pd.date_range('2024-01-05', periods=3),
                'Номер карты': ['*1234', '*5678', '*9012'],
                'Статус': ['OK', 'OK', 'OK'],
                'Сумма операции': [-100, -200, -300],
                'Валюта операции': ['RUB'] * 3,
                'Сумма платежа': [100, 200, 300],
                'Валюта платежа': ['RUB'] * 3,
                'Кэшбэк': [1, 2, 3],
                'Категория': ['Супермаркеты', 'Кафе', 'Транспорт'],
                'MCC': ['5411', '5812', '4111'],
                'Описание': ['Покупка 1', 'Покупка 2', 'Покупка 3'],
                'Бонусы (включая кэшбэк)': [1, 2, 3],
                'Округление на инвесткопилку': [0.5, 0.5, 0.5],
                'Сумма операции с округлением': [-99.5, -198.0, -297.0]
            }
            mock_df = pd.DataFrame(data)
            mock_read.return_value = mock_df

            result = load_transactions_from_excel(str(mock_excel_file))

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            assert 'Дата операции' in result.columns
            # Проверяем, что числовые столбцы обработаны
            assert result['Сумма операции'].dtype in ['int64', 'float64']

    def test_load_transactions_file_not_found(self, tmp_path):
        """Тест обработки отсутствия файла"""
        non_existent_file = tmp_path / 'nonexistent.xlsx'

        with pytest.raises(FileNotFoundError) as exc_info:
            load_transactions_from_excel(str(non_existent_file))

        assert "не найден" in str(exc_info.value) or "Файл не найден" in str(exc_info.value)

    def test_load_transactions_permission_error(self, mock_excel_file):
        """Тест обработки ошибки прав доступа"""
        # Мокаем os.path.exists чтобы файл "существовал"
        with patch('src.utils.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('src.utils.os.access') as mock_access:
                mock_access.return_value = False  # Нет прав на чтение

                with pytest.raises(PermissionError) as exc_info:
                    load_transactions_from_excel(str(mock_excel_file))

                assert "Нет прав" in str(exc_info.value)

    def test_load_transactions_empty_file(self, mock_excel_file, mock_os_path):
        """Тест обработки пустого файла"""
        with patch('src.utils.pd.read_excel') as mock_read:
            mock_read.return_value = pd.DataFrame()

            with pytest.raises(ValueError) as exc_info:
                load_transactions_from_excel(str(mock_excel_file))

            assert "пуст" in str(exc_info.value) or "пустой" in str(exc_info.value)

    def test_load_transactions_missing_columns(self, mock_excel_file, mock_os_path):
        """Тест обработки отсутствия обязательных столбцов"""
        with patch('src.utils.pd.read_excel') as mock_read:
            # DataFrame только с некоторыми столбцами
            mock_df = pd.DataFrame({
                'Дата операции': pd.date_range('2024-01-01', periods=3),
                'Номер карты': ['*1234', '*5678', '*9012'],
                'Сумма операции': [-100, -200, -300],
                # Нет других обязательных столбцов
            })
            mock_read.return_value = mock_df

            with pytest.raises(ValueError) as exc_info:
                load_transactions_from_excel(str(mock_excel_file))

            assert "отсутствуют обязательные столбцы" in str(exc_info.value)

    @pytest.mark.parametrize("column_name", [
        'Дата операции',
        'Номер карты',
        'Сумма операции',
        'Категория',
        'Кэшбэк'
    ])
    def test_required_columns_present(self, mock_excel_file, mock_os_path, column_name):
        """Параметризованный тест проверки обязательных столбцов"""
        with patch('src.utils.pd.read_excel') as mock_read:
            # Создаем DataFrame со всеми обязательными столбцами
            data = {
                'Дата операции': pd.date_range('2024-01-01', periods=3),
                'Дата платежа': pd.date_range('2024-01-05', periods=3),
                'Номер карты': ['*1234', '*5678', '*9012'],
                'Статус': ['OK', 'OK', 'OK'],
                'Сумма операции': [-100, -200, -300],
                'Валюта операции': ['RUB'] * 3,
                'Сумма платежа': [100, 200, 300],
                'Валюта платежа': ['RUB'] * 3,
                'Кэшбэк': [1, 2, 3],
                'Категория': ['Супермаркеты', 'Кафе', 'Транспорт'],
                'MCC': ['5411', '5812', '4111'],
                'Описание': ['Test'] * 3,
                'Бонусы (включая кэшбэк)': [1, 2, 3],
                'Округление на инвесткопилку': [0.5, 0.5, 0.5],
                'Сумма операции с округлением': [-99.5, -198.0, -297.0]
            }
            mock_read.return_value = pd.DataFrame(data)

            result = load_transactions_from_excel(str(mock_excel_file))

            assert column_name in result.columns

    def test_numeric_columns_filled_with_zero(self, mock_excel_file, mock_os_path):
        """Тест заполнения пропущенных числовых значений нулями"""
        with patch('src.utils.pd.read_excel') as mock_read:
            # Создаем DataFrame с NaN в числовых столбцах
            data = {
                'Дата операции': pd.date_range('2024-01-01', periods=3),
                'Дата платежа': pd.date_range('2024-01-05', periods=3),
                'Номер карты': ['*1234', '*5678', '*9012'],
                'Статус': ['OK', 'OK', 'OK'],
                'Сумма операции': [-100, None, -300],  # Одно значение None
                'Валюта операции': ['RUB'] * 3,
                'Сумма платежа': [100, 200, None],  # Одно значение None
                'Валюта платежа': ['RUB'] * 3,
                'Кэшбэк': [None, 2, 3],  # Одно значение None
                'Категория': ['A', 'B', 'C'],
                'MCC': ['5411', '5812', '4111'],
                'Описание': ['Test'] * 3,
                'Бонусы (включая кэшбэк)': [1, None, 3],  # Одно значение None
                'Округление на инвесткопилку': [None, 0.5, 0.5],  # Одно значение None
                'Сумма операции с округлением': [-99.5, -198.0, None]  # Одно значение None
            }
            mock_read.return_value = pd.DataFrame(data)

            result = load_transactions_from_excel(str(mock_excel_file))

            # Проверяем, что нет NaN в числовых столбцах
            numeric_columns = [
                'Сумма операции',
                'Сумма платежа',
                'Кэшбэк',
                'Бонусы (включая кэшбэк)',
                'Округление на инвесткопилку',
                'Сумма операции с округлением'
            ]

            for column in numeric_columns:
                if column in result.columns:
                    assert not result[column].isnull().any(), f"В столбце {column} есть NaN"

    def test_string_columns_filled_with_empty(self, mock_excel_file, mock_os_path):
        """Тест заполнения пропущенных строковых значений пустыми строками"""
        with patch('src.utils.pd.read_excel') as mock_read:
            # Создаем DataFrame с NaN в строковых столбцах
            data = {
                'Дата операции': pd.date_range('2024-01-01', periods=3),
                'Дата платежа': pd.date_range('2024-01-05', periods=3),
                'Номер карты': ['*1234', None, '*9012'],  # Одно значение None
                'Статус': [None, 'OK', 'OK'],  # Одно значение None
                'Сумма операции': [-100, -200, -300],
                'Валюта операции': ['RUB'] * 3,
                'Сумма платежа': [100, 200, 300],
                'Валюта платежа': ['RUB'] * 3,
                'Кэшбэк': [1, 2, 3],
                'Категория': ['A', None, 'C'],  # Одно значение None
                'MCC': ['5411', '5812', '4111'],
                'Описание': ['Test 1', 'Test 2', None],  # Одно значение None
                'Бонусы (включая кэшбэк)': [1, 2, 3],
                'Округление на инвесткопилку': [0.5, 0.5, 0.5],
                'Сумма операции с округлением': [-99.5, -198.0, -297.0]
            }
            mock_read.return_value = pd.DataFrame(data)

            result = load_transactions_from_excel(str(mock_excel_file))

            # Проверяем, что нет NaN в строковых столбцах
            string_columns = ['Номер карты', 'Статус', 'Категория', 'Описание']

            for column in string_columns:
                if column in result.columns:
                    assert not result[column].isnull().any(), f"В столбце {column} есть NaN"
                    # Все значения должны быть строками (даже пустыми)
                    assert all(isinstance(val, str) for val in result[column])


class TestFilterTransactionsByDate:
    """Тесты для функции filter_transactions_by_date"""

    def test_filter_transactions_by_date(self, sample_dataframe):
        """Тест фильтрации транзакций по дате"""
        # Убедимся, что в sample_dataframe есть правильные даты
        test_date = datetime(2024, 1, 5, 12, 0, 0)

        result = filter_transactions_by_date(sample_dataframe, test_date)

        # Проверяем, что все транзакции в январе 2024
        assert all(result['Дата операции'].dt.month == 1)
        assert all(result['Дата операции'].dt.year == 2024)

        # Проверяем, что даты <= концу дня test_date
        end_of_day = test_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        assert all(result['Дата операции'] <= end_of_day)

    def test_filter_empty_dataframe(self):
        """Тест фильтрации пустого DataFrame"""
        empty_df = pd.DataFrame(columns=['Дата операции'])
        test_date = datetime(2024, 1, 1)

        result = filter_transactions_by_date(empty_df, test_date)

        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    def test_filter_no_transactions_in_period(self, sample_dataframe):
        """Тест фильтрации когда нет транзакций в периоде"""
        future_date = datetime(2025, 1, 1)

        result = filter_transactions_by_date(sample_dataframe, future_date)

        # В исходных данных нет транзакций за 2025 год
        assert len(result) == 0

    @pytest.mark.parametrize("test_date,expected_count", [
        (datetime(2024, 1, 1), 1),  # Первый день месяца
        (datetime(2024, 1, 5), 5),  # Пятый день
        (datetime(2024, 1, 10), 10),  # Последний день (если 10 транзакций)
    ])
    def test_filter_different_dates(self, test_date, expected_count):
        """Параметризованный тест фильтрации по разным датам"""
        # Создаем тестовый DataFrame с 10 транзакциями
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = {
            'Дата операции': dates,
            'Номер карты': [f"*{i:04d}" for i in range(10)],
            'Сумма операции': [-100] * 10,
            'Категория': ['Test'] * 10
        }
        df = pd.DataFrame(data)

        # Убедимся, что даты datetime
        df['Дата операции'] = pd.to_datetime(df['Дата операции'])

        result = filter_transactions_by_date(df, test_date)

        assert len(result) == expected_count


class TestGetTimeGreeting:
    """Тесты для функции get_time_greeting"""

    @pytest.mark.parametrize("hour,expected_greeting", [
        (4, "Доброе утро"),  # Граница утра
        (5, "Доброе утро"),  # Утро
        (11, "Доброе утро"),  # Граница утра/дня
        (12, "Добрый день"),  # День
        (16, "Добрый день"),  # День
        (17, "Добрый вечер"),  # Вечер
        (22, "Добрый вечер"),  # Вечер
        (23, "Доброй ночи"),  # Ночь
        (0, "Доброй ночи"),  # Ночь
        (3, "Доброй ночи"),  # Ночь
    ])
    def test_get_time_greeting(self, hour, expected_greeting):
        """Параметризованный тест приветствий по времени"""
        test_date = datetime(2024, 1, 1, hour, 0, 0)

        result = get_time_greeting(test_date)

        assert result == expected_greeting

    def test_get_time_greeting_edge_cases(self):
        """Тест граничных случаев"""
        test_cases = [
            (datetime(2024, 1, 1, 3, 59, 59), "Доброй ночи"),
            (datetime(2024, 1, 1, 4, 0, 0), "Доброе утро"),
            (datetime(2024, 1, 1, 11, 59, 59), "Доброе утро"),
            (datetime(2024, 1, 1, 12, 0, 0), "Добрый день"),
            (datetime(2024, 1, 1, 16, 59, 59), "Добрый день"),
            (datetime(2024, 1, 1, 17, 0, 0), "Добрый вечер"),
            (datetime(2024, 1, 1, 22, 59, 59), "Добрый вечер"),
            (datetime(2024, 1, 1, 23, 0, 0), "Доброй ночи"),
        ]

        for test_date, expected in test_cases:
            result = get_time_greeting(test_date)
            assert result == expected, f"Failed for {test_date.hour}:{test_date.minute}:{test_date.second}"


class TestLoadUserSettings:
    """Тесты для функции load_user_settings"""

    def test_load_user_settings_success(self, tmp_path):
        """Тест успешной загрузки настроек"""
        # Создаем временный файл настроек
        settings_data = {
            "user_currencies": ["USD", "EUR", "JPY"],
            "user_stocks": ["AAPL", "GOOGL", "TSLA"]
        }

        # Создаем структуру папок: project_root/data/
        project_root = tmp_path / "project"
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True)

        settings_file = data_dir / "user_settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False)

        # Мокаем os.path.abspath и os.path.dirname
        with patch('src.utils.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = str(project_root / "src" / "utils.py")

            result = load_user_settings()

            assert isinstance(result, dict)
            assert 'user_currencies' in result
            assert 'user_stocks' in result
            assert result['user_currencies'] == ["USD", "EUR", "JPY"]
            assert result['user_stocks'] == ["AAPL", "GOOGL", "TSLA"]

    def test_load_user_settings_file_not_found(self, tmp_path):
        """Тест загрузки при отсутствии файла настроек"""
        # Создаем структуру папок без файла настроек
        project_root = tmp_path / "project"
        src_dir = project_root / "src"
        src_dir.mkdir(parents=True)

        with patch('src.utils.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = str(src_dir / "utils.py")

            result = load_user_settings()

            # Должны вернуться значения по умолчанию
            assert result['user_currencies'] == ['USD', 'EUR', 'GBP']
            assert result['user_stocks'] == ['AAPL', 'GOOGL', 'MSFT']

    def test_load_user_settings_invalid_json(self, tmp_path):
        """Тест загрузки при невалидном JSON"""
        # Создаем структуру папок
        project_root = tmp_path / "project"
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True)

        # Создаем файл с невалидным JSON
        settings_file = data_dir / "user_settings.json"
        settings_file.write_text('{invalid json}')

        with patch('src.utils.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = str(project_root / "src" / "utils.py")

            result = load_user_settings()

            # Должны вернуться значения по умолчанию
            assert result['user_currencies'] == ['USD', 'EUR', 'GBP']
            assert result['user_stocks'] == ['AAPL', 'GOOGL', 'MSFT']

    def test_load_user_settings_missing_keys(self, tmp_path):
        """Тест загрузки настроек с отсутствующими ключами"""
        # Создаем структуру папок
        project_root = tmp_path / "project"
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True)

        # Создаем файл с неполными настройками
        incomplete_settings = {"some_other_key": "value"}
        settings_file = data_dir / "user_settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete_settings, f, ensure_ascii=False)

        with patch('src.utils.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = str(project_root / "src" / "utils.py")

            result = load_user_settings()

            # Должны вернуться значения по умолчанию
            assert result['user_currencies'] == ['USD', 'EUR', 'GBP']
            assert result['user_stocks'] == ['AAPL', 'GOOGL', 'MSFT']

    def test_load_user_settings_alternative_path(self, tmp_path):
        """Тест загрузки настроек из альтернативного пути"""
        # Создаем структуру папок с файлом в старом расположении
        project_root = tmp_path / "project"
        project_root.mkdir(parents=True)

        # Файл в старом расположении (не в папке data)
        old_settings_file = project_root / "user_settings.json"
        settings_data = {
            "user_currencies": ["USD", "CAD"],
            "user_stocks": ["MSFT", "AMZN"]
        }
        with open(old_settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False)

        with patch('src.utils.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = str(project_root / "src" / "utils.py")

            result = load_user_settings()

            # Должны загрузиться настройки из альтернативного пути
            assert result['user_currencies'] == ["USD", "CAD"]
            assert result['user_stocks'] == ["MSFT", "AMZN"]


# ==================== ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ДЛЯ ПОЛНОГО ПОКРЫТИЯ ====================

class TestUtilsIntegration:
    """Интеграционные тесты для utils.py"""

    def test_full_pipeline(self, tmp_path):
        """Тест полного пайплайна работы с данными"""
        # Создаем тестовый Excel файл
        excel_data = {
            'Дата операции': pd.date_range('2024-01-01', periods=5, freq='D'),
            'Дата платежа': pd.date_range('2024-01-05', periods=5, freq='D'),
            'Номер карты': ['*1234', '*5678', '*9012', '*3456', '*7890'],
            'Статус': ['OK'] * 5,
            'Сумма операции': [-100, -200, -300, -400, -500],
            'Валюта операции': ['RUB'] * 5,
            'Сумма платежа': [100, 200, 300, 400, 500],
            'Валюта платежа': ['RUB'] * 5,
            'Кэшбэк': [1.0, 2.0, 3.0, 4.0, 5.0],
            'Категория': ['Супермаркеты', 'Кафе', 'Транспорт', 'Аптеки', 'Развлечения'],
            'MCC': ['5411', '5812', '4111', '5122', '7999'],
            'Описание': ['Покупка'] * 5,
            'Бонусы (включая кэшбэк)': [1.0, 2.0, 3.0, 4.0, 5.0],
            'Округление на инвесткопилку': [0.5] * 5,
            'Сумма операции с округлением': [-99.5, -198.0, -297.0, -396.0, -495.0]
        }

        df = pd.DataFrame(excel_data)

        # Убедимся, что даты действительно datetime
        df['Дата операции'] = pd.to_datetime(df['Дата операции'])
        df['Дата платежа'] = pd.to_datetime(df['Дата платежа'])

        excel_file = tmp_path / 'test_operations.xlsx'

        # Сохраняем с index=False чтобы избежать дополнительных колонок
        df.to_excel(excel_file, index=False)

        # Создаем файл настроек
        settings_data = {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "GOOGL"]
        }

        project_root = tmp_path / "project"
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True)

        settings_file = data_dir / "user_settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False)

        # Мокаем пути
        with patch('src.utils.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = str(project_root / "src" / "utils.py")

            # 1. Загружаем настройки
            settings = load_user_settings()
            assert settings['user_currencies'] == ["USD", "EUR"]

            # 2. Загружаем транзакции
            # Нужно замокать pd.read_excel для правильного парсинга дат
            with patch('src.utils.pd.read_excel') as mock_read_excel:
                mock_read_excel.return_value = df

                transactions = load_transactions_from_excel(str(excel_file))
                assert len(transactions) == 5

                # 3. Фильтруем по дате
                test_date = datetime(2024, 1, 3)
                filtered = filter_transactions_by_date(transactions, test_date)
                assert len(filtered) == 3  # 1, 2, 3 января

            # 4. Получаем приветствие
            greeting = get_time_greeting(datetime(2024, 1, 1, 14, 0, 0))
            assert greeting == "Добрый день"

    def test_error_handling_integration(self):
        """Тест интеграции обработки ошибок"""

        @handle_exception
        def test_function():
            raise RuntimeError("Integration test error")

        with pytest.raises(RuntimeError) as exc_info:
            test_function()

        assert "Integration test error" in str(exc_info.value)
