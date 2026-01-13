"""
Конфигурация и фикстуры для тестов
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from faker import Faker

# Добавляем src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

fake = Faker('ru_RU')


# ==================== ФИКСТУРЫ ДЛЯ ТЕСТОВЫХ ДАННЫХ ====================

@pytest.fixture
def fake_transactions_data():
    """Генерация фейковых данных транзакций"""
    transactions = []
    for i in range(100):
        transaction = {
            'Дата операции': fake.date_between(start_date='-1y', end_date='today'),
            'Дата платежа': fake.date_between(start_date='-1y', end_date='today'),
            'Номер карты': f"*{fake.credit_card_number()[-4:]}",
            'Статус': fake.random_element(['OK', 'FAILED', 'PENDING']),
            'Сумма операции': fake.pyfloat(
                left_digits=4,
                right_digits=2,
                positive=False,  # Могут быть и доходы и расходы
                min_value=-10000,
                max_value=10000
            ),
            'Валюта операции': 'RUB',
            'Сумма платежа': abs(fake.pyfloat(left_digits=4, right_digits=2, positive=True)),
            'Валюта платежа': 'RUB',
            'Кэшбэк': fake.pyfloat(left_digits=2, right_digits=2, positive=True, max_value=100),
            'Категория': fake.random_element([
                'Супермаркеты', 'Кафе и рестораны', 'Транспорт',
                'Аптеки', 'Развлечения', 'Одежда', 'Красота', 'Пополнения'
            ]),
            'MCC': str(fake.random_int(min=1000, max=9999)),
            'Описание': fake.sentence(nb_words=5),
            'Бонусы (включая кэшбэк)': fake.pyfloat(left_digits=2, right_digits=2, positive=True, max_value=50),
            'Округление на инвесткопилку': fake.pyfloat(left_digits=1, right_digits=2, positive=True, max_value=10),
            'Сумма операции с округлением': fake.pyfloat(left_digits=4, right_digits=2, positive=False)
        }
        transactions.append(transaction)

    return pd.DataFrame(transactions)


@pytest.fixture
def sample_dataframe():
    """Фикстура с тестовым DataFrame"""
    data = {
        'Дата операции': pd.date_range('2024-01-01', periods=10, freq='D'),
        'Дата платежа': pd.date_range('2024-01-05', periods=10, freq='D'),
        'Номер карты': [f"*{i:04d}" for i in range(10)],
        'Статус': ['OK'] * 10,
        'Сумма операции': [-100, -200, -300, 1000, -150, -250, -350, -450, 500, -100],
        'Валюта операции': ['RUB'] * 10,
        'Сумма платежа': [100, 200, 300, 1000, 150, 250, 350, 450, 500, 100],
        'Валюта платежа': ['RUB'] * 10,
        'Кэшбэк': [1.0, 2.0, 3.0, 0, 1.5, 2.5, 3.5, 4.5, 0, 1.0],
        'Категория': ['Супермаркеты', 'Кафе и рестораны', 'Транспорт',
                      'Пополнения', 'Аптеки', 'Супермаркеты', 'Кафе и рестораны',
                      'Транспорт', 'Пополнения', 'Развлечения'],
        'MCC': ['5411', '5812', '4111', '0000', '5122', '5411', '5812', '4111', '0000', '7999'],
        'Описание': ['Покупка в магазине'] * 10,
        'Бонусы (включая кэшбэк)': [1.0, 2.0, 3.0, 0, 1.5, 2.5, 3.5, 4.5, 0, 1.0],
        'Округление на инвесткопилку': [0.5] * 10,
        'Сумма операции с округлением': [-99.5, -198.0, -297.0, 1000, -148.5, -247.5,
                                         -346.5, -445.5, 500, -99.0]
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_excel_file(tmp_path):
    """Создание временного Excel файла для тестов"""
    df = pd.DataFrame({
        'Дата операции': pd.date_range('2024-01-01', periods=5, freq='D'),
        'Дата платежа': pd.date_range('2024-01-05', periods=5, freq='D'),
        'Номер карты': ['*1234', '*5678', '*9012', '*3456', '*7890'],
        'Статус': ['OK'] * 5,
        'Сумма операции': [-100, -200, -300, 500, -400],
        'Категория': ['Супермаркеты', 'Кафе', 'Транспорт', 'Пополнения', 'Аптеки'],
    })

    file_path = tmp_path / 'test_operations.xlsx'
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def mock_settings_file(tmp_path):
    """Создание временного файла настроек"""
    settings = {
        "user_currencies": ["USD", "EUR", "GBP"],
        "user_stocks": ["AAPL", "GOOGL", "MSFT"]
    }

    file_path = tmp_path / 'user_settings.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False)

    return file_path


@pytest.fixture
def mock_env_file(tmp_path):
    """Создание временного .env файла"""
    env_content = """CURRENCY_API_KEY=test_currency_key
STOCK_API_KEY=test_stock_key"""

    file_path = tmp_path / '.env'
    file_path.write_text(env_content)
    return file_path


# ==================== ФИКСТУРЫ ДЛЯ МОКОВ ====================

@pytest.fixture
def mock_requests():
    """Мок для requests"""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_datetime():
    """Мок для datetime"""
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        mock_dt.strptime.side_effect = lambda *args, **kw: datetime.strptime(*args, **kw)
        yield mock_dt


@pytest.fixture
def mock_os_path():
    """Мок для os.path"""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        with patch('os.access') as mock_access:
            mock_access.return_value = True
            yield mock_exists, mock_access


@pytest.fixture
def mock_pandas_read_excel():
    """Мок для pandas.read_excel"""
    with patch('pandas.read_excel') as mock_read:
        yield mock_read


# ==================== ФИКСТУРЫ ДЛЯ ПАРАМЕТРИЗАЦИИ ====================

@pytest.fixture(params=[
    (2024, 1, 31),  # Январь
    (2024, 2, 29),  # Февраль (високосный)
    (2024, 6, 30),  # Июнь
    (2024, 12, 31),  # Декабрь
])
def month_test_cases(request):
    """Параметризация тестов по месяцам"""
    return request.param


@pytest.fixture(params=[
    ('USD', 'EUR', 'GBP'),
    ('EUR', 'JPY', 'CNY'),
    ('RUB', 'USD', 'EUR'),
])
def currency_test_cases(request):
    """Параметризация тестов по валютам"""
    return request.param


@pytest.fixture(params=[
    ('AAPL', 'GOOGL', 'MSFT'),
    ('TSLA', 'AMZN', 'NVDA'),
    ('META', 'NFLX', 'AMD'),
])
def stock_test_cases(request):
    """Параметризация тестов по акциям"""
    return request.param


# ==================== ДОПОЛНИТЕЛЬНЫЕ ФИКСТУРЫ ====================

@pytest.fixture
def fixed_date():
    """Фиксированная дата для тестов"""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def sample_cashback_result():
    """Пример результата анализа кэшбэка"""
    return {
        'Супермаркеты': 1250.50,
        'Кафе и рестораны': 850.25,
        'Транспорт': 450.75,
        'Аптеки': 250.30,
        'Развлечения': 150.15
    }


@pytest.fixture
def mock_api_responses():
    """Моки ответов API"""
    return {
        'currency': {
            'conversion_rates': {
                'USD': 1.0,
                'EUR': 0.92,
                'GBP': 0.79,
                'RUB': 90.0
            }
        },
        'stock': {
            'AAPL': {'Global Quote': {'05. price': '185.25'}},
            'GOOGL': {'Global Quote': {'05. price': '138.75'}},
            'MSFT': {'Global Quote': {'05. price': '375.50'}}
        }
    }


# ==================== ФИКСТУРЫ ДЛЯ ЗАВИСИМОСТЕЙ ====================

@pytest.fixture
def mock_services():
    """Мок для модуля services"""
    with patch.dict('sys.modules', {
        'services': Mock(),
        'src.services': Mock(),
        'src.services.cashback_analysis': Mock(),
        'src.services.export_utils': Mock()
    }) as mock_dict:
        # Настраиваем моки для конкретных функций
        mock_services_module = mock_dict['src.services']
        mock_services_module.analyze_cashback_categories = Mock(return_value={})
        mock_services_module.get_top_categories_by_cashback = Mock(return_value=[])
        mock_services_module.get_monthly_cashback_report = Mock(return_value={})
        mock_services_module.export_cashback_analysis_to_json = Mock(return_value='{}')

        yield mock_services_module


@pytest.fixture
def mock_utils():
    """Мок для модуля utils"""
    with patch.dict('sys.modules', {
        'utils': Mock(),
        'src.utils': Mock(),
        'src.utils.date_utils': Mock(),
        'src.utils.file_operations': Mock()
    }) as mock_dict:
        # Настраиваем моки для конкретных функций
        mock_utils_module = mock_dict['src.utils']
        mock_utils_module.handle_exception = lambda func: func
        mock_utils_module.logger = Mock()
        mock_utils_module.load_transactions_from_excel = Mock()
        mock_utils_module.filter_transactions_by_date = Mock()
        mock_utils_module.process_transactions = Mock()
        mock_utils_module.load_user_settings = Mock()
        mock_utils_module.get_time_greeting = Mock(return_value='Добрый день')

        yield mock_utils_module


@pytest.fixture
def mock_all_dependencies():
    """Комплексный мок всех зависимостей"""
    with patch('src.views.os.path.exists') as mock_exists, \
         patch('src.views.os.access') as mock_access, \
         patch('src.views.os.getenv') as mock_getenv, \
         patch('src.views.load_transactions_from_excel') as mock_load, \
         patch('src.views.filter_transactions_by_date') as mock_filter, \
         patch('src.views.process_transactions') as mock_process, \
         patch('src.views.load_user_settings') as mock_settings, \
         patch('src.views.get_time_greeting') as mock_greeting, \
         patch('src.views.get_currency_rates') as mock_currency, \
         patch('src.views.get_stock_prices') as mock_stocks, \
         patch('src.views.services.analyze_cashback_categories') as mock_analyze, \
         patch('src.views.services.get_top_categories_by_cashback') as mock_top, \
         patch('src.views.services.get_monthly_cashback_report') as mock_report, \
         patch('src.views.services.export_cashback_analysis_to_json') as mock_export:

        # Настраиваем возвращаемые значения
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_getenv.return_value = 'test_api_key'
        mock_load.return_value = Mock()
        mock_filter.return_value = Mock()
        mock_process.return_value = {'cards': [], 'top_transactions': []}
        mock_settings.return_value = {'user_currencies': [], 'user_stocks': []}
        mock_greeting.return_value = 'Добрый день'
        mock_currency.return_value = []
        mock_stocks.return_value = []
        mock_analyze.return_value = {}
        mock_top.return_value = []
        mock_report.return_value = {}
        mock_export.return_value = '{}'

        yield {
            'os.path.exists': mock_exists,
            'os.access': mock_access,
            'os.getenv': mock_getenv,
            'load_transactions_from_excel': mock_load,
            'filter_transactions_by_date': mock_filter,
            'process_transactions': mock_process,
            'load_user_settings': mock_settings,
            'get_time_greeting': mock_greeting,
            'get_currency_rates': mock_currency,
            'get_stock_prices': mock_stocks,
            'analyze_cashback_categories': mock_analyze,
            'get_top_categories_by_cashback': mock_top,
            'get_monthly_cashback_report': mock_report,
            'export_cashback_analysis_to_json': mock_export
        }
