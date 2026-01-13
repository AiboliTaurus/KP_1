"""
Тесты для модуля views.py
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.views import (
    generate_cashback_recommendations,
    generate_month_suggestions,
    get_available_data_months,
    get_cashback_analysis,
    get_currency_rates,
    get_default_currency_rates,
    get_default_stock_price,
    get_default_stock_prices,
    get_main_page_data,
    get_main_page_data_with_cashback,
    get_stock_prices,
)


class TestGetMainPageData:
    """Тесты для функции get_main_page_data"""

    def test_get_main_page_data_success(self, sample_dataframe, mock_requests):
        """Тест успешного получения данных главной страницы"""
        # Мокаем ВСЕ зависимости, включая os.access
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                with patch('src.views.load_transactions_from_excel') as mock_load:
                    with patch('src.views.filter_transactions_by_date') as mock_filter:
                        with patch('src.views.process_transactions') as mock_process:
                            with patch('src.views.load_user_settings') as mock_settings:
                                with patch('src.views.get_currency_rates') as mock_currency:
                                    with patch('src.views.get_stock_prices') as mock_stocks:
                                        with patch('src.views.get_time_greeting') as mock_greeting:
                                            # Настраиваем моки
                                            mock_exists.return_value = True
                                            mock_access.return_value = True
                                            mock_load.return_value = sample_dataframe
                                            mock_filter.return_value = sample_dataframe
                                            mock_process.return_value = {
                                                'cards': [{'card_number': '*1234', 'total_amount': -100}],
                                                'top_transactions': [{'date': '01.01.2024', 'amount': 100}]
                                            }
                                            mock_settings.return_value = {
                                                'user_currencies': ['USD', 'EUR'],
                                                'user_stocks': ['AAPL']
                                            }
                                            mock_currency.return_value = [
                                                {'currency': 'USD', 'rate': 1.0}
                                            ]
                                            mock_stocks.return_value = [
                                                {'stock': 'AAPL', 'price': 185.0}
                                            ]
                                            mock_greeting.return_value = 'Добрый день'

                                            # Вызываем функцию
                                            result = get_main_page_data(
                                                '2024-01-15 10:30:00',
                                                '/test/path.xlsx'
                                            )

                                            # Проверяем результат
                                            assert isinstance(result, dict)
                                            assert 'greeting' in result
                                            assert 'cards' in result
                                            assert 'top_transactions' in result
                                            assert 'currency_rates' in result
                                            assert 'stock_prices' in result

                                            # Проверяем вызовы
                                            mock_load.assert_called_once_with('/test/path.xlsx')
                                            mock_filter.assert_called_once()
                                            mock_process.assert_called_once()
                                            mock_settings.assert_called_once()
                                            mock_currency.assert_called_once_with(['USD', 'EUR'])
                                            mock_stocks.assert_called_once_with(['AAPL'])

    def test_get_main_page_data_exception(self):
        """Тест обработки исключения"""
        # Мокаем os.path.exists и os.access
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                mock_exists.return_value = True
                mock_access.return_value = True
                with patch('src.views.load_transactions_from_excel') as mock_load:
                    mock_load.side_effect = Exception("Test error")

                    with pytest.raises(Exception) as exc_info:
                        get_main_page_data('2024-01-15 10:30:00', '/test/path.xlsx')

                    assert "Test error" in str(exc_info.value)


class TestGetCurrencyRates:
    """Тесты для функции get_currency_rates"""

    def test_get_currency_rates_success(self, mock_requests):
        """Тест успешного получения курсов валют"""
        # Мокаем ответ API
        mock_response = Mock()
        mock_response.json.return_value = {
            'conversion_rates': {
                'USD': 1.0,
                'EUR': 0.92,
                'GBP': 0.79,
                'JPY': 148.0
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Мокаем API ключ
        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'

            result = get_currency_rates(['USD', 'EUR', 'GBP'])

            assert isinstance(result, list)
            # USD всегда добавляется автоматически, если его нет в списке
            # В данном случае USD уже есть, так что 3 валюты
            assert len(result) == 3

            # Проверяем структуру
            for rate in result:
                assert 'currency' in rate
                assert 'rate' in rate
                assert isinstance(rate['rate'], (int, float))

    def test_get_currency_rates_api_error(self, mock_requests):
        """Тест обработки ошибки API"""
        mock_requests.side_effect = Exception("API error")

        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'

            result = get_currency_rates(['USD', 'EUR'])

            # Должны вернуться значения по умолчанию
            assert isinstance(result, list)
            assert len(result) > 0

    def test_get_currency_rates_no_api_key(self):
        """Тест получения курсов без API ключа"""
        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = None  # Нет API ключа

            result = get_currency_rates(['USD', 'EUR'])

            # Должны вернуться значения по умолчанию
            assert isinstance(result, list)
            # USD + EUR = 2 валюты (USD не дублируется, если уже есть в списке)
            assert len(result) == 2
            assert result[0]['currency'] == 'USD'
            assert result[1]['currency'] == 'EUR'

    def test_get_currency_rates_default_function(self):
        """Тест функции get_default_currency_rates"""
        result = get_default_currency_rates(['USD', 'EUR', 'JPY'])

        assert isinstance(result, list)
        assert len(result) == 3

        # Проверяем, что курс USD = 1.0
        usd_rate = next(r for r in result if r['currency'] == 'USD')
        assert usd_rate['rate'] == 1.0


class TestGetStockPrices:
    """Тесты для функции get_stock_prices"""

    def test_get_stock_prices_success(self, mock_requests):
        """Тест успешного получения цен на акции"""
        # Мокаем ответы API для разных акций
        mock_responses = [
            Mock(**{
                'json.return_value': {
                    'Global Quote': {'05. price': '185.25'}
                },
                'raise_for_status.return_value': None
            }),
            Mock(**{
                'json.return_value': {
                    'Global Quote': {'05. price': '138.75'}
                },
                'raise_for_status.return_value': None
            })
        ]
        mock_requests.side_effect = mock_responses

        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'
            with patch('src.views.time.sleep'):  # Мокаем sleep

                result = get_stock_prices(['AAPL', 'GOOGL'])

                assert isinstance(result, list)
                assert len(result) == 2

                for stock in result:
                    assert 'stock' in stock
                    assert 'price' in stock
                    assert isinstance(stock['price'], float)

    def test_get_stock_prices_api_error(self, mock_requests):
        """Тест обработки ошибки API"""
        mock_requests.side_effect = Exception("API error")

        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'

            result = get_stock_prices(['AAPL', 'GOOGL'])

            # Должны вернуться значения по умолчанию
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]['stock'] == 'AAPL'

    def test_get_stock_prices_no_api_key(self):
        """Тест получения цен без API ключа"""
        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = None  # Нет API ключа

            result = get_stock_prices(['AAPL', 'GOOGL'])

            # Должны вернуться значения по умолчанию
            assert isinstance(result, list)
            assert len(result) == 2

    def test_get_default_stock_price(self):
        """Тест функции get_default_stock_price"""
        test_cases = [
            ('AAPL', 185.0),
            ('GOOGL', 138.0),
            ('MSFT', 375.0),
            ('UNKNOWN', 100.0),  # Значение по умолчанию
        ]

        for stock, expected_price in test_cases:
            result = get_default_stock_price(stock)
            assert result == expected_price

    def test_get_default_stock_prices(self):
        """Тест функции get_default_stock_prices"""
        stocks = ['AAPL', 'GOOGL', 'UNKNOWN']

        result = get_default_stock_prices(stocks)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]['stock'] == 'AAPL'
        assert result[0]['price'] == 185.0


class TestDataAnalysisFunctions:
    """Тесты для функций анализа данных"""

    def test_get_available_data_months_success(self, sample_dataframe):
        """Тест получения доступных месяцев"""
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                with patch('src.views.load_transactions_from_excel') as mock_load:
                    mock_exists.return_value = True
                    mock_access.return_value = True
                    mock_load.return_value = sample_dataframe

                    result = get_available_data_months('/test/path.xlsx')

                    assert isinstance(result, dict)
                    assert 'data_source' in result
                    assert 'total_transactions' in result
                    assert 'date_range' in result
                    assert 'available_months' in result
                    assert 'suggestions' in result

    def test_generate_month_suggestions(self):
        """Тест генерации предложений по месяцам"""
        years_data = {
            '2023': [
                {'month': 1, 'month_str': '2023-01', 'transactions_count': 100},
                {'month': 2, 'month_str': '2023-02', 'transactions_count': 150},
            ],
            '2024': [
                {'month': 1, 'month_str': '2024-01', 'transactions_count': 200},
            ]
        }

        result = generate_month_suggestions(years_data)

        assert isinstance(result, list)
        assert len(result) == 2  # Два предложения
        assert any('Последний доступный месяц' in s for s in result)
        assert any('Наиболее активный год' in s for s in result)

    def test_get_main_page_data_with_cashback(self):
        """Тест получения расширенных данных"""
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                mock_exists.return_value = True
                mock_access.return_value = True
                with patch('src.views.get_main_page_data') as mock_main:
                    with patch('src.views.get_cashback_analysis') as mock_cashback:
                        # Настраиваем моки
                        mock_main.return_value = {
                            'greeting': 'Добрый день',
                            'cards': [],
                            'top_transactions': []
                        }
                        mock_cashback.return_value = {
                            'cashback_by_category': {'A': 100},
                            'top_categories': [{'category': 'A', 'cashback': 100}],
                            'total_cashback': 100
                        }

                        result = get_main_page_data_with_cashback(
                            '2024-01-15 10:30:00',
                            '/test/path.xlsx'
                        )

                        assert isinstance(result, dict)
                        assert 'greeting' in result
                        assert 'cashback_analysis' in result
                        assert 'summary' in result['cashback_analysis']
                        assert 'top_3_categories' in result['cashback_analysis']


# ==================== ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ====================

class TestEdgeCases:
    """Тесты граничных случаев"""

    def test_get_currency_rates_empty_list(self):
        """Тест получения курсов для пустого списка валют"""
        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'

            result = get_currency_rates([])

            assert isinstance(result, list)
            # Проверяем поведение функции - может возвращать пустой список
            # или список с USD по умолчанию

    def test_get_stock_prices_empty_list(self):
        """Тест получения цен для пустого списка акций"""
        result = get_stock_prices([])

        assert isinstance(result, list)
        assert len(result) == 0

    def test_generate_cashback_recommendations_edge_cases(self):
        """Тест граничных случаев генерации рекомендаций"""
        # Тест с None значениями
        result = generate_cashback_recommendations(None, None)
        assert isinstance(result, list)

        # Тест с нулевым кэшбэком
        result = generate_cashback_recommendations({'A': 0, 'B': 0}, [])
        assert isinstance(result, list)

    def test_get_cashback_analysis_file_not_found(self):
        """Тест анализа кэшбэка при отсутствии файла"""
        with patch('src.views.os.path.exists') as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(FileNotFoundError):
                get_cashback_analysis('2024-01-15 10:30:00', '/nonexistent/path.xlsx')


class TestMockUsage:
    """Тесты использования моков"""

    def test_mock_chain_calls(self, mock_requests):
        """Тест цепочки вызовов с моками"""
        # Создаем сложный мок с цепочкой вызовов
        mock_response = Mock()
        mock_response.json.return_value = {'conversion_rates': {'USD': 1.0}}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_key'

            result = get_currency_rates(['USD'])

            # Проверяем вызовы
            mock_requests.assert_called_once()
            mock_response.json.assert_called_once()
            mock_response.raise_for_status.assert_called_once()

            assert isinstance(result, list)

    def test_multiple_patches(self):
        """Тест одновременного использования нескольких patch"""
        with patch('src.views.os.path.exists') as mock_exists, \
             patch('src.views.os.access') as mock_access, \
             patch('src.views.load_transactions_from_excel') as mock_load, \
             patch('src.views.filter_transactions_by_date') as mock_filter, \
             patch('src.views.process_transactions') as mock_process:

            # Настраиваем все моки
            mock_exists.return_value = True
            mock_access.return_value = True
            mock_load.return_value = Mock()
            mock_filter.return_value = Mock()
            mock_process.return_value = {'cards': [], 'top_transactions': []}

            # Создаем дополнительные моки для других зависимостей
            with patch('src.views.load_user_settings') as mock_settings, \
                 patch('src.views.get_currency_rates') as mock_currency, \
                 patch('src.views.get_stock_prices') as mock_stocks, \
                 patch('src.views.get_time_greeting') as mock_greeting:

                mock_settings.return_value = {'user_currencies': [], 'user_stocks': []}
                mock_currency.return_value = []
                mock_stocks.return_value = []
                mock_greeting.return_value = 'Тест'

                result = get_main_page_data('2024-01-15 10:30:00', '/test/path.xlsx')

                assert isinstance(result, dict)


# ==================== ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ДЛЯ ПОЛНОГО ПОКРЫТИЯ ====================

class TestComprehensiveCoverage:
    """Дополнительные тесты для достижения 80%+ покрытия"""

    @pytest.mark.parametrize("currencies,expected_min_length", [
        ([], 0),
        (['USD'], 1),
        (['USD', 'EUR'], 2),
        (['EUR', 'GBP'], 2),
    ])
    def test_get_currency_rates_parametrized(self, currencies, expected_min_length, mock_requests):
        """Параметризованный тест получения курсов валют"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'conversion_rates': {
                'USD': 1.0,
                'EUR': 0.92,
                'GBP': 0.79,
                'JPY': 148.0
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'

            result = get_currency_rates(currencies)

            assert isinstance(result, list)
            if expected_min_length > 0:
                assert len(result) >= expected_min_length

    @pytest.mark.parametrize("date_str", [
        "2024-01-15 05:30:00",
        "2024-01-15 12:30:00",
        "2024-01-15 18:30:00",
        "2024-01-15 23:30:00",
    ])
    def test_get_main_page_data_different_times(self, date_str, sample_dataframe):
        """Тест получения данных главной страницы в разное время суток"""
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                with patch('src.views.load_transactions_from_excel') as mock_load:
                    with patch('src.views.filter_transactions_by_date') as mock_filter:
                        with patch('src.views.process_transactions') as mock_process:
                            with patch('src.views.load_user_settings') as mock_settings:
                                with patch('src.views.get_currency_rates') as mock_currency:
                                    with patch('src.views.get_stock_prices') as mock_stocks:
                                        with patch('src.views.get_time_greeting') as mock_greeting:
                                            # Настраиваем моки
                                            mock_exists.return_value = True
                                            mock_access.return_value = True
                                            mock_load.return_value = sample_dataframe
                                            mock_filter.return_value = sample_dataframe
                                            mock_process.return_value = {
                                                'cards': [{'card_number': '*1234', 'total_amount': -100}],
                                                'top_transactions': [{'date': '01.01.2024', 'amount': 100}]
                                            }
                                            mock_settings.return_value = {
                                                'user_currencies': ['USD'],
                                                'user_stocks': ['AAPL']
                                            }
                                            mock_currency.return_value = [{'currency': 'USD', 'rate': 1.0}]
                                            mock_stocks.return_value = [{'stock': 'AAPL', 'price': 185.0}]
                                            mock_greeting.return_value = 'Тестовое приветствие'

                                            result = get_main_page_data(date_str, '/test/path.xlsx')

                                            assert isinstance(result, dict)
                                            assert 'greeting' in result

    def test_get_default_currency_rates_edge_cases(self):
        """Тест граничных случаев для get_default_currency_rates"""
        # Пустой список
        result = get_default_currency_rates([])
        assert isinstance(result, list)

        # Неизвестная валюта
        result = get_default_currency_rates(['UNKNOWN'])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['currency'] == 'UNKNOWN'

    @pytest.mark.parametrize("cashback_data,top_categories", [
        (None, None),
        ({}, []),
        ({'A': 100}, []),
        ({}, [{'category': 'A', 'cashback': 100}]),
    ])
    def test_generate_cashback_recommendations_comprehensive(self, cashback_data, top_categories):
        """Комплексный тест генерации рекомендаций"""
        result = generate_cashback_recommendations(cashback_data, top_categories)
        assert isinstance(result, list)


# ==================== ТЕСТЫ ОБРАБОТКИ ОШИБОК ====================

class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_get_main_page_data_file_not_found(self):
        """Тест обработки отсутствия файла"""
        with patch('src.views.os.path.exists') as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(FileNotFoundError):
                get_main_page_data('2024-01-15 10:30:00', '/nonexistent/path.xlsx')

    def test_get_main_page_data_permission_error(self):
        """Тест обработки ошибки прав доступа"""
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                mock_exists.return_value = True
                mock_access.return_value = False  # Нет прав на чтение

                with pytest.raises(PermissionError):
                    get_main_page_data('2024-01-15 10:30:00', '/test/path.xlsx')

    def test_get_currency_rates_network_error(self, mock_requests):
        """Тест обработки сетевой ошибки при получении курсов"""
        mock_requests.side_effect = ConnectionError("Network error")

        with patch('src.views.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test_api_key'

            result = get_currency_rates(['USD', 'EUR'])

            # Должны вернуться значения по умолчанию
            assert isinstance(result, list)
            assert len(result) > 0

    def test_get_cashback_analysis_exception_handling(self, sample_dataframe):
        """Тест обработки исключений в анализе кэшбэка"""
        with patch('src.views.os.path.exists') as mock_exists:
            with patch('src.views.os.access') as mock_access:
                mock_exists.return_value = True
                mock_access.return_value = True
                with patch('src.views.load_transactions_from_excel') as mock_load:
                    mock_load.side_effect = Exception("Ошибка загрузки данных")

                    with pytest.raises(Exception) as exc_info:
                        get_cashback_analysis('2024-01-15 10:30:00', '/test/path.xlsx')

                    assert "Ошибка загрузки данных" in str(exc_info.value)
