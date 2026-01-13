import json
import logging
from datetime import datetime
from functools import reduce
from itertools import groupby
from operator import itemgetter
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# ==================== ОСНОВНЫЕ ФУНКЦИИ ДЛЯ АНАЛИЗА КЭШБЭКА ====================

def analyze_cashback_categories(
        df: pd.DataFrame,
        year: int,
        month: int
) -> Dict[str, float]:
    """
    Анализирует выгодность категорий повышенного кешбэка.

    Args:
        df: DataFrame с транзакциями
        year: Год для анализа
        month: Месяц для анализа (1-12)

    Returns:
        Словарь с категориями и суммой кэшбэка по ним
    """
    logger.info(f"Анализ кэшбэка за {month}.{year}")

    try:
        # 1. Фильтрация данных за указанный месяц и год
        filtered_data = filter_transactions_by_month(df, year, month)

        # 2. Группировка по категориям
        grouped_by_category = group_transactions_by_category(filtered_data)

        # 3. Расчет кэшбэка по категориям
        cashback_by_category = calculate_cashback_by_category(grouped_by_category)

        # 4. Сортировка по убыванию кэшбэка
        sorted_cashback = sort_cashback_descending(cashback_by_category)

        # 5. Форматирование результата
        result = format_cashback_result(sorted_cashback)

        logger.info(f"Анализ завершен. Найдено {len(result)} категорий")
        return result

    except Exception as e:
        logger.error(f"Ошибка анализа кэшбэка: {str(e)}")
        raise


# ==================== ФУНКЦИИ ФУНКЦИОНАЛЬНОГО ПРОГРАММИРОВАНИЯ ====================

def filter_transactions_by_month(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """
    Фильтрует транзакции по году и месяцу с использованием функционального подхода.
    """
    # Используем лямбда-функцию для фильтрации
    mask = df['Дата операции'].apply(
        lambda x: x.year == year and x.month == month
    )
    filtered_df = df[mask]
    logger.info(f"Отфильтровано {len(filtered_df)} транзакций за {month}.{year}")
    return filtered_df


def group_transactions_by_category(df: pd.DataFrame) -> Dict[str, List[Dict]]:
    """
    Группирует транзакции по категориям с использованием functools.
    """
    if df.empty:
        return {}

    # Преобразуем DataFrame в список словарей
    transactions = df.to_dict('records')

    # Сортируем по категории для группировки
    transactions.sort(key=lambda x: x['Категория'])

    # Группируем по категории с использованием itertools.groupby
    grouped = {}
    for category, group in groupby(transactions, key=lambda x: x['Категория']):
        grouped[category] = list(group)

    logger.info(f"Сгруппировано по {len(grouped)} категориям")
    return grouped


def calculate_cashback_by_category(grouped_transactions: Dict[str, List[Dict]]) -> Dict[str, float]:
    """
    Рассчитывает кэшбэк по каждой категории.
    """
    if not grouped_transactions:
        return {}

    # Используем map для преобразования категорий
    cashback_calculation = map(
        lambda item: (
            item[0],  # Название категории
            reduce(
                lambda acc, transaction: acc + calculate_transaction_cashback(transaction),
                item[1],  # Список транзакций
                0.0  # Начальное значение
            )
        ),
        grouped_transactions.items()
    )

    return dict(cashback_calculation)


def calculate_transaction_cashback(transaction: Dict) -> float:
    """
    Рассчитывает кэшбэк для одной транзакции.
    """
    try:
        amount = float(transaction.get('Сумма операции', 0))
        category = str(transaction.get('Категория', ''))

        # Базовая ставка кэшбэка - 1%
        base_cashback_rate = 0.01

        # Дополнительный бонус для определенных категорий
        bonus_categories = {
            'Аптеки': 0.03,  # 3% кэшбэк
            'Супермаркеты': 0.02,  # 2% кэшбэк
            'Кафе и рестораны': 0.02,  # 2% кэшбэк
            'Транспорт': 0.02,  # 2% кэшбэк
            'Развлечения': 0.015,  # 1.5% кэшбэк
        }

        # Определяем ставку кэшбэка
        cashback_rate = bonus_categories.get(category, base_cashback_rate)

        # Расчет кэшбэка
        cashback = amount * cashback_rate

        # Ограничение максимального кэшбэка (если нужно)
        max_cashback_per_transaction = 1000  # Максимум 1000 рублей за транзакцию
        cashback = min(cashback, max_cashback_per_transaction)

        return cashback

    except Exception as e:
        logger.warning(f"Ошибка расчета кэшбэка для транзакции: {str(e)}")
        return 0.0


def sort_cashback_descending(cashback_dict: Dict[str, float]) -> List[Tuple[str, float]]:
    """
    Сортирует категории по убыванию кэшбэка.
    """
    # Используем itemgetter для сортировки
    sorted_items = sorted(
        cashback_dict.items(),
        key=itemgetter(1),
        reverse=True
    )
    return sorted_items


def format_cashback_result(sorted_cashback: List[Tuple[str, float]]) -> Dict[str, float]:
    """
    Форматирует результат в словарь с округленными значениями.
    """
    # Округляем значения до 2 знаков после запятой
    return {
        category: round(amount, 2)
        for category, amount in sorted_cashback
        if amount > 0  # Исключаем категории с нулевым кэшбэком
    }


# ==================== СТАРЫЕ ФУНКЦИИ (ДЛЯ СОВМЕСТИМОСТИ) ====================

from utils import handle_exception


@handle_exception
def process_transactions(df: pd.DataFrame) -> Dict:
    """
    Обрабатывает транзакции для главной страницы.
    Оставлено для обратной совместимости.
    """
    try:
        if df.empty:
            logger.warning("Нет транзакций для обработки")
            return {
                'cards': [],
                'top_transactions': []
            }

        # Обработка транзакций по картам
        logger.info("Начинаем обработку транзакций по картам")

        # Используем функциональный подход для группировки
        cards_data = df.groupby('Номер карты').agg({
            'Сумма операции': 'sum'
        }).reset_index()

        # Рассчитываем кэшбэк (1% от суммы) с использованием map
        cards_data['cashback'] = cards_data['Сумма операции'].map(lambda x: x * 0.01)

        # Форматируем для вывода с использованием list comprehension
        cards_list = [
            {
                "card_number": str(row['Номер карты']),
                "total_amount": float(row['Сумма операции']),
                "cashback": float(row['cashback'])
            }
            for _, row in cards_data.iterrows()
        ]

        # Топ транзакций
        logger.info("Формируем топ транзакций")
        top_transactions = df.sort_values(
            by='Сумма операции', ascending=False
        ).head(5)

        return {
            'cards': cards_list,
            'top_transactions': format_top_transactions(top_transactions)
        }

    except Exception as e:
        logger.error(f"Ошибка при обработке транзакций: {str(e)}")
        raise


def format_top_transactions(transactions: pd.DataFrame) -> List[Dict]:
    """
    Форматирует топ транзакций.
    """
    if transactions.empty:
        return []

    # Используем list comprehension для функционального стиля
    return [
        {
            "date": row['Дата операции'].strftime('%d.%m.%Y'),
            "amount": float(row['Сумма операции']),
            "category": str(row['Категория']),
            "description": str(row['Описание']),
            "card_number": str(row['Номер карты'])
        }
        for _, row in transactions.iterrows()
    ]


# ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ АНАЛИЗА ====================

def get_monthly_cashback_report(df: pd.DataFrame, year: int) -> Dict[str, Dict[str, float]]:
    """
    Генерирует отчет по кэшбэку за все месяцы года.

    Args:
        df: DataFrame с транзакциями
        year: Год для анализа

    Returns:
        Словарь с месяцами и анализом кэшбэка
    """
    report = {}

    for month in range(1, 13):
        try:
            month_report = analyze_cashback_categories(df, year, month)
            if month_report:  # Добавляем только если есть данные
                report[f"{month:02d}.{year}"] = month_report
        except Exception as e:
            logger.warning(f"Ошибка анализа для месяца {month}: {str(e)}")

    return report


def get_top_categories_by_cashback(
        df: pd.DataFrame,
        year: int,
        month: int,
        top_n: int = 5
) -> List[Dict[str, any]]:
    """
    Возвращает топ N категорий по кэшбэку.
    """
    cashback_analysis = analyze_cashback_categories(df, year, month)

    # Преобразуем в список словарей и берем топ N
    top_categories = [
        {"category": category, "cashback": amount}
        for category, amount in list(cashback_analysis.items())[:top_n]
    ]

    return top_categories


def export_cashback_analysis_to_json(
        df: pd.DataFrame,
        year: int,
        month: int,
        output_path: str = None
) -> str:
    """
    Экспортирует анализ кэшбэка в JSON файл.
    """
    analysis = analyze_cashback_categories(df, year, month)

    # Добавляем метаданные
    result = {
        "year": year,
        "month": month,
        "analysis_date": datetime.now().isoformat(),
        "categories_count": len(analysis),
        "total_cashback": sum(analysis.values()),
        "categories": analysis
    }

    json_str = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        default=str
    )

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        logger.info(f"Анализ сохранен в {output_path}")

    return json_str
