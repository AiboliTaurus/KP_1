import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

from services import process_transactions
from utils import (
    filter_transactions_by_date,
    get_time_greeting,
    handle_exception,
    load_transactions_from_excel,
    load_user_settings,
)

# Загружаем переменные окружения
load_dotenv('../.env')

logger = logging.getLogger(__name__)


@handle_exception
def get_main_page_data(date_str: str, excel_path: str) -> dict:
    logger.info("Получение данных для главной страницы")
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        df = load_transactions_from_excel(excel_path)
        df = filter_transactions_by_date(df, date)
        processed_data = process_transactions(df)

        # Загружаем настройки
        user_settings = load_user_settings()
        logger.info(f"Загружены настройки: {user_settings}")

        # Получаем курсы валют и цены на акции
        currency_rates = get_currency_rates(user_settings['user_currencies'])
        stock_prices = get_stock_prices(user_settings['user_stocks'])

        return {
            "greeting": get_time_greeting(date),
            "cards": processed_data['cards'],
            "top_transactions": processed_data['top_transactions'],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices
        }
    except Exception as e:
        logger.error(f"Произошла ошибка в get_main_page_data: {str(e)}")
        raise


@handle_exception
def get_currency_rates(user_currencies=None):
    logger.info("Получение курсов валют")
    api_key = os.getenv('CURRENCY_API_KEY')

    # Если не переданы валюты, используем настройки по умолчанию
    if user_currencies is None:
        user_currencies = ['USD', 'EUR', 'GBP']

    # Если API ключ не задан, возвращаем значения по умолчанию
    if not api_key:
        logger.warning("API ключ для валют не задан, возвращаю значения по умолчанию")
        return get_default_currency_rates(user_currencies)

    try:
        response = requests.get(
            f'https://v6.exchangerate-api.com/v6/{api_key}/latest/USD',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Формируем список курсов валют
        conversion_rates = data.get('conversion_rates', {})

        # Всегда добавляем USD как базовую валюту
        if 'USD' not in user_currencies:
            user_currencies = ['USD'] + user_currencies

        return [
            {
                "currency": currency,
                "rate": conversion_rates.get(currency, 1.0 if currency == 'USD' else 0)
            }
            for currency in user_currencies
        ]

    except requests.exceptions.RequestException as req_err:
        logger.error(f"Ошибка при получении курсов: {str(req_err)}")
        return get_default_currency_rates(user_currencies)
    except Exception as e:
        logger.error(f"Ошибка получения курсов валют: {str(e)}")
        return get_default_currency_rates(user_currencies)


def get_default_currency_rates(currencies):
    """Возвращает значения по умолчанию для курсов валют"""
    default_rates = {
        'USD': 1.0,
        'EUR': 0.92,
        'GBP': 0.79,
        'RUB': 90.0,
        'JPY': 148.0,
        'CNY': 7.2
    }

    return [
        {
            "currency": currency,
            "rate": default_rates.get(currency, 1.0 if currency == 'USD' else 0)
        }
        for currency in currencies
    ]


@handle_exception
def get_stock_prices(user_stocks=None):
    logger.info("Получение цен на акции")
    api_key = os.getenv('STOCK_API_KEY')

    # Если не переданы акции, используем настройки по умолчанию
    if user_stocks is None:
        user_stocks = ['AAPL', 'GOOGL', 'MSFT']

    # Если API ключ не задан, возвращаем значения по умолчанию
    if not api_key:
        logger.warning("API ключ для акций не задан, возвращаю значения по умолчанию")
        return get_default_stock_prices(user_stocks)

    prices = []

    for i, stock in enumerate(user_stocks):
        try:
            # Формируем URL для запроса
            url = 'https://www.alphavantage.co/query'
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': stock,
                'apikey': api_key
            }

            logger.info(f"Запрос цены для акции {stock} ({i + 1}/{len(user_stocks)})")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if 'Global Quote' in data and '05. price' in data['Global Quote']:
                price = float(data['Global Quote']['05. price'])
                logger.info(f"Цена для {stock}: {price}")
            else:
                logger.warning(f"Не удалось получить цену для {stock}, ответ: {data}")
                price = get_default_stock_price(stock)

            prices.append({
                "stock": stock,
                "price": price
            })

            # Задержка для избежания лимита API (бесплатный тариф - 5 запросов в минуту)
            if i < len(user_stocks) - 1:  # Не делаем задержку после последней акции
                logger.info("Пауза 15 секунд для соблюдения лимитов API...")
                time.sleep(15)

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Ошибка при получении цены для {stock}: {str(req_err)}")
            prices.append({
                "stock": stock,
                "price": get_default_stock_price(stock)
            })
        except Exception as e:
            logger.error(f"Ошибка при обработке данных для {stock}: {str(e)}")
            prices.append({
                "stock": stock,
                "price": get_default_stock_price(stock)
            })

    return prices


def get_default_stock_price(stock):
    """Возвращает значение по умолчанию для акции"""
    default_prices = {
        'AAPL': 185.0,
        'GOOGL': 138.0,
        'MSFT': 375.0,
        'AMZN': 150.0,
        'TSLA': 235.0,
        'NVDA': 500.0,
        'META': 350.0
    }
    return default_prices.get(stock, 100.0)


def get_default_stock_prices(stocks):
    """Возвращает значения по умолчанию для списка акций"""
    return [{"stock": stock, "price": get_default_stock_price(stock)} for stock in stocks]


# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С КЭШБЭКОМ ====================

@handle_exception
def get_cashback_analysis(date_str: str, excel_path: str) -> dict:
    """
    Получает анализ кэшбэка за месяц указанной даты

    Args:
        date_str: Дата в формате YYYY-MM-DD HH:MM:SS
        excel_path: Путь к файлу Excel

    Returns:
        Словарь с анализом кэшбэка
    """
    logger.info("Получение анализа кэшбэка")
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        year = date.year
        month = date.month

        # Загружаем данные
        df = load_transactions_from_excel(excel_path)

        # Импортируем функции анализа из services
        from services import analyze_cashback_categories, get_monthly_cashback_report, get_top_categories_by_cashback

        # Анализируем кэшбэк
        cashback_data = analyze_cashback_categories(df, year, month)
        top_categories = get_top_categories_by_cashback(df, year, month, top_n=5)

        # Получаем отчет за весь год
        yearly_report = get_monthly_cashback_report(df, year)

        return {
            "analysis_date": date_str,
            "year": year,
            "month": month,
            "cashback_by_category": cashback_data,
            "top_categories": top_categories,
            "total_cashback": sum(cashback_data.values()) if cashback_data else 0,
            "yearly_report_summary": {
                "months_analyzed": len(yearly_report),
                "total_cashback_year": sum(
                    sum(month_data.values()) for month_data in yearly_report.values()
                ) if yearly_report else 0
            }
        }

    except Exception as e:
        logger.error(f"Ошибка при получении анализа кэшбэка: {str(e)}")
        raise


@handle_exception
def get_cashback_report(date_str: str, excel_path: str, export_path: Optional[str] = None) -> dict:
    """
    Генерирует полный отчет по кэшбэку и экспортирует его

    Args:
        date_str: Дата в формате YYYY-MM-DD HH:MM:SS
        excel_path: Путь к файлу Excel
        export_path: Путь для экспорта отчета (опционально)

    Returns:
        Словарь с отчетом
    """
    logger.info("Генерация отчета по кэшбэку")
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        year = date.year
        month = date.month

        # Загружаем данные
        df = load_transactions_from_excel(excel_path)

        # Импортируем функции анализа из services
        from services import analyze_cashback_categories, get_monthly_cashback_report, get_top_categories_by_cashback

        # Анализируем кэшбэк
        cashback_data = analyze_cashback_categories(df, year, month)
        top_categories = get_top_categories_by_cashback(df, year, month, top_n=10)

        # Получаем отчет за весь год
        yearly_report = get_monthly_cashback_report(df, year)

        # Формируем отчет
        report = {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "analysis_date": date_str,
                "year": year,
                "month": month,
                "data_source": excel_path,
                "total_transactions": len(df)
            },
            "cashback_analysis": {
                "monthly_analysis": cashback_data,
                "top_categories": top_categories,
                "total_cashback": sum(cashback_data.values()) if cashback_data else 0,
                "categories_count": len(cashback_data)
            },
            "yearly_overview": {
                "months_with_data": list(yearly_report.keys()),
                "total_months": len(yearly_report),
                "yearly_total_cashback": sum(
                    sum(month_data.values()) for month_data in yearly_report.values()
                ) if yearly_report else 0
            },
            "recommendations": generate_cashback_recommendations(cashback_data, top_categories)
        }

        # Экспортируем отчет, если указан путь
        if export_path:
            export_dir = os.path.dirname(export_path)
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir)

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Отчет сохранен в: {export_path}")

        return report

    except Exception as e:
        logger.error(f"Ошибка при генерации отчета по кэшбэку: {str(e)}")
        raise


def generate_cashback_recommendations(cashback_data: Dict[str, float],
                                      top_categories: List[Dict]) -> List[Dict]:
    """
    Генерирует рекомендации по кэшбэку на основе анализа

    Args:
        cashback_data: Данные по кэшбэку по категориям
        top_categories: Топ категории по кэшбэку

    Returns:
        Список рекомендаций
    """
    if not cashback_data or not top_categories:
        return [{"type": "warning", "message": "Недостаточно данных для рекомендаций"}]

    recommendations = []
    total_cashback = sum(cashback_data.values())

    # Рекомендация по топ-категориям
    if top_categories:
        top_category = top_categories[0]
        recommendations.append({
            "type": "info",
            "title": "Наиболее выгодная категория",
            "message": f"Категория '{top_category['category']}' принесла {top_category['cashback']:.2f} руб. кэшбэка",
            "action": f"Рассмотрите повышенный кэшбэк для категории '{top_category['category']}'"
        })

    # Рекомендация по распределению
    if len(cashback_data) >= 3:
        top_3_total = sum(item['cashback'] for item in top_categories[:3])
        percentage = (top_3_total / total_cashback * 100) if total_cashback > 0 else 0

        if percentage > 70:
            recommendations.append({
                "type": "warning",
                "title": "Концентрация трат",
                "message": f"Топ-3 категории составляют {percentage:.1f}% всего кэшбэка",
                "action": "Рассмотрите диверсификацию трат для увеличения общего кэшбэка"
            })

    # Рекомендация по маленьким категориям
    small_categories = {cat: amount for cat, amount in cashback_data.items()
                        if amount < total_cashback * 0.05 and amount > 0}

    if small_categories:
        recommendations.append({
            "type": "suggestion",
            "title": "Категории с низким кэшбэком",
            "message": f"Обнаружено {len(small_categories)} категорий с небольшим кэшбэком",
            "action": "Рассмотрите оптимизацию трат в этих категориях или выбор других банковских продуктов"
        })

    # Общая рекомендация
    if total_cashback > 0:
        recommendations.append({
            "type": "success",
            "title": "Общий результат",
            "message": f"Общий кэшбэк за месяц: {total_cashback:.2f} руб.",
            "action": "Продолжайте отслеживать траты для максимизации кэшбэка"
        })

    return recommendations


@handle_exception
def get_available_data_months(excel_path: str) -> dict:
    """
    Получает список доступных месяцев в данных

    Args:
        excel_path: Путь к файлу Excel

    Returns:
        Словарь с доступными месяцами
    """
    logger.info("Получение списка доступных месяцев")
    try:
        df = load_transactions_from_excel(excel_path)

        if 'Дата операции' not in df.columns:
            return {"error": "Столбец 'Дата операции' не найден"}

        # Извлекаем уникальные годы и месяцы
        df['Год_Месяц'] = df['Дата операции'].dt.strftime('%Y-%m')
        months_stats = df['Год_Месяц'].value_counts().sort_index()

        # Группируем по годам
        years_data = {}
        for month_str, count in months_stats.items():
            year, month = month_str.split('-')
            if year not in years_data:
                years_data[year] = []
            years_data[year].append({
                "month": int(month),
                "month_str": month_str,
                "transactions_count": int(count)
            })

        # Сортируем месяцы в каждом году
        for year in years_data:
            years_data[year].sort(key=lambda x: x['month'])

        return {
            "data_source": excel_path,
            "total_transactions": len(df),
            "date_range": {
                "min": df['Дата операции'].min().strftime('%Y-%m-%d'),
                "max": df['Дата операции'].max().strftime('%Y-%m-%d')
            },
            "available_months": {
                "by_year": years_data,
                "all_months": [
                    {
                        "year_month": month_str,
                        "transactions": int(count)
                    }
                    for month_str, count in months_stats.items()
                ]
            },
            "suggestions": generate_month_suggestions(years_data)
        }

    except Exception as e:
        logger.error(f"Ошибка при получении списка месяцев: {str(e)}")
        raise


def generate_month_suggestions(years_data: Dict) -> List[str]:
    """
    Генерирует предложения по месяцам для анализа

    Args:
        years_data: Данные по месяцам сгруппированные по годам

    Returns:
        Список предложений
    """
    suggestions = []

    if not years_data:
        return suggestions

    # Предложение по последнему году
    last_year = sorted(years_data.keys())[-1]
    if years_data[last_year]:
        last_month = years_data[last_year][-1]
        suggestions.append(
            f"Последний доступный месяц: {last_month['month_str']} "
            f"({last_month['transactions_count']} транзакций)"
        )

    # Предложение по году с максимальным количеством транзакций
    year_totals = []
    for year, months in years_data.items():
        total = sum(month['transactions_count'] for month in months)
        year_totals.append((year, total))

    if year_totals:
        busiest_year = max(year_totals, key=lambda x: x[1])
        suggestions.append(
            f"Наиболее активный год: {busiest_year[0]} "
            f"({busiest_year[1]} транзакций)"
        )

    return suggestions


# ==================== ФУНКЦИИ ДЛЯ ИНТЕГРАЦИИ С ГЛАВНОЙ СТРАНИЦЕЙ ====================

@handle_exception
def get_main_page_data_with_cashback(date_str: str, excel_path: str) -> dict:
    """
    Получает данные для главной страницы с добавлением анализа кэшбэка

    Args:
        date_str: Дата в формате YYYY-MM-DD HH:MM:SS
        excel_path: Путь к файлу Excel

    Returns:
        Расширенный словарь с данными для главной страницы
    """
    logger.info("Получение данных для главной страницы с анализом кэшбэка")
    try:
        # Получаем основные данные
        main_data = get_main_page_data(date_str, excel_path)

        # Получаем анализ кэшбэка
        cashback_analysis = get_cashback_analysis(date_str, excel_path)

        # Объединяем данные
        result = {
            **main_data,
            "cashback_analysis": {
                "summary": {
                    "total_cashback": cashback_analysis.get("total_cashback", 0),
                    "top_category": cashback_analysis.get("top_categories", [{}])[0]
                    if cashback_analysis.get("top_categories") else {},
                    "categories_count": len(cashback_analysis.get("cashback_by_category", {}))
                },
                "top_3_categories": cashback_analysis.get("top_categories", [])[:3]
            }
        }

        return result

    except Exception as e:
        logger.error(f"Ошибка при получении расширенных данных: {str(e)}")
        # Возвращаем основные данные даже если анализ кэшбэка не удался
        return get_main_page_data(date_str, excel_path)


# ==================== ТЕСТОВЫЕ ФУНКЦИИ ====================

def test_views_functions():
    """
    Тестирование функций модуля views
    """

    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ФУНКЦИЙ VIEWS")
    print("=" * 80)

    try:
        # Тестовые данные
        test_date = "2021-01-15 10:30:00"
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        excel_path = os.path.join(root_dir, 'data', 'operations.xlsx')

        print(f"Тестовая дата: {test_date}")
        print(f"Путь к файлу: {excel_path}")

        if not os.path.exists(excel_path):
            print("❌ Файл не найден")
            return

        # Тест 1: Основные данные
        print("\n1. Тест get_main_page_data:")
        main_data = get_main_page_data(test_date, excel_path)
        print(f"   ✅ Успешно. Карт: {len(main_data['cards'])}, "
              f"транзакций: {len(main_data['top_transactions'])}")

        # Тест 2: Анализ кэшбэка
        print("\n2. Тест get_cashback_analysis:")
        cashback_data = get_cashback_analysis(test_date, excel_path)
        print(f"   ✅ Успешно. Категорий: {len(cashback_data['cashback_by_category'])}, "
              f"общий кэшбэк: {cashback_data['total_cashback']:.2f}")

        # Тест 3: Доступные месяцы
        print("\n3. Тест get_available_data_months:")
        months_data = get_available_data_months(excel_path)
        if 'available_months' in months_data:
            print(f"   ✅ Успешно. Доступно лет: {len(months_data['available_months']['by_year'])}, "
                  f"всего месяцев: {len(months_data['available_months']['all_months'])}")

        # Тест 4: Расширенные данные
        print("\n4. Тест get_main_page_data_with_cashback:")
        extended_data = get_main_page_data_with_cashback(test_date, excel_path)
        print(f"   ✅ Успешно. Содержит анализ кэшбэка: {'cashback_analysis' in extended_data}")

        print("\n" + "=" * 80)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Запуск тестов при прямом выполнении файла
    test_views_functions()
