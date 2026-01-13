import argparse
import json
import logging
import os
import sys
from datetime import datetime

# Добавляем папку src в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from views import get_main_page_data


def setup_logging():
    """Настройка системы логирования"""
    # Создаем папку для логов, если ее нет
    log_dir = '../logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, 'app.log'), encoding='utf-8')
        ]
    )


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Приложение для анализа транзакций и кэшбэка (данные за 2018-2021 годы)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default="2021-01-15 10:30:00",
        help="Дата в формате YYYY-MM-DD HH:MM:SS (по умолчанию 2021-01-15 10:30:00)"
    )
    parser.add_argument(
        "--excel-path",
        type=str,
        help="Пользовательский путь к файлу Excel с операциями"
    )
    parser.add_argument(
        "--settings-path",
        type=str,
        help="Пользовательский путь к файлу настроек JSON"
    )
    # НОВЫЙ АРГУМЕНТ для анализа кэшбэка
    parser.add_argument(
        "--analyze-cashback",
        type=str,
        help="Анализ кэшбэка за указанный месяц в формате ГГГГ-ММ (например, 2020-01)"
    )
    parser.add_argument(
        "--export-cashback",
        type=str,
        help="Путь для экспорта анализа кэшбэка (опционально, по умолчанию в data/)"
    )
    return parser.parse_args()


def run_cashback_analysis(args):
    """Запуск анализа кэшбэка"""
    logger = logging.getLogger(__name__)

    try:
        # Парсим дату для анализа кэшбэка
        year, month = map(int, args.analyze_cashback.split('-'))

        # Проверяем корректность месяца
        if month < 1 or month > 12:
            raise ValueError(f"Некорректный месяц: {month}. Должен быть от 1 до 12")

        # Проверяем корректность года (для ваших данных 2018-2021)
        if year < 2018 or year > 2021:
            logger.warning(f"Год {year} вне диапазона ваших данных (2018-2021)")
            # Не прерываем выполнение, просто предупреждаем

        # Загружаем данные
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        excel_path = args.excel_path or os.path.join(root_dir, 'data', 'operations.xlsx')

        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Файл Excel не найден: {excel_path}")

        logger.info(f"Анализ кэшбэка за {month:02d}.{year}")

        # Импортируем необходимые модули
        from services import (
            analyze_cashback_categories,
            export_cashback_analysis_to_json,
            get_top_categories_by_cashback,
        )
        from utils import load_transactions_from_excel

        # Загружаем данные
        logger.info("Загрузка данных из Excel...")
        df = load_transactions_from_excel(excel_path)
        logger.info(f"Загружено {len(df)} транзакций")

        # Проверяем диапазон дат в данных
        if 'Дата операции' in df.columns:
            min_year = df['Дата операции'].dt.year.min()
            max_year = df['Дата операции'].dt.year.max()
            logger.info(f"Диапазон дат в данных: {min_year}-{max_year}")

        # Проверяем, есть ли данные за указанный период
        if 'Дата операции' in df.columns:
            dates_in_period = df[
                (df['Дата операции'].dt.year == year) &
                (df['Дата операции'].dt.month == month)
                ]
            if len(dates_in_period) == 0:
                logger.warning(f"Нет транзакций за {month:02d}.{year}")
                # Показываем доступные месяцы
                available_months = sorted(df['Дата операции'].dt.strftime('%Y-%m').unique())
                if len(available_months) > 0:
                    logger.info(f"Доступные месяцы: {available_months}")
                    print("\n📊 Доступные месяцы в данных:")
                    for available_month in available_months:
                        print(f"  • {available_month}")

        # Анализируем кэшбэк
        logger.info("Выполнение анализа кэшбэка...")
        result = analyze_cashback_categories(df, year, month)

        if not result:
            print(f"\n⚠️ Нет данных для анализа кэшбэка за {month:02d}.{year}")
            return

        # Определяем путь для экспорта
        if args.export_cashback:
            export_path = args.export_cashback
            # Создаем директорию, если не существует
            export_dir = os.path.dirname(export_path)
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir)
        else:
            export_path = os.path.join(
                root_dir,
                'data',
                f'cashback_analysis_{year}_{month:02d}.json'
            )

        # Экспортируем в файл
        export_cashback_analysis_to_json(df, year, month, export_path)

        # Выводим результаты
        total_cashback = sum(result.values())

        print(f"\n{'=' * 60}")
        print(f"АНАЛИЗ КЭШБЭКА ЗА {month:02d}.{year}")
        print(f"{'=' * 60}")
        print(f"Всего категорий: {len(result)}")
        print(f"Общий кэшбэк: {total_cashback:.2f} руб.")
        print("\nПодробный анализ:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # Выводим топ-5 категорий
        top_categories = get_top_categories_by_cashback(df, year, month, top_n=5)
        if top_categories:
            print(f"\n{'=' * 60}")
            print("ТОП-5 КАТЕГОРИЙ ПО КЭШБЭКУ")
            print(f"{'=' * 60}")
            for i, item in enumerate(top_categories, 1):
                print(f"{i:2d}. {item['category'][:40]:40} {item['cashback']:8.2f} руб.")

        print(f"\n{'=' * 60}")
        print(f"Полный отчет сохранен в: {export_path}")
        print(f"{'=' * 60}")

        logger.info("Анализ кэшбэка завершен успешно")

    except ValueError as e:
        if "unpack" in str(e):
            logger.error(f"Некорректный формат даты: {args.analyze_cashback}. Используйте ГГГГ-ММ")
            print(f"Ошибка: некорректный формат даты: {args.analyze_cashback}")
            print("Используйте формат: ГГГГ-ММ (например, 2020-01)")
        else:
            logger.error(f"Ошибка в параметрах: {str(e)}")
            print(f"Ошибка: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при анализе кэшбэка: {str(e)}", exc_info=True)
        print(f"Произошла ошибка: {str(e)}")


def main():
    """Основная функция приложения"""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        args = parse_arguments()

        # =========== НОВАЯ ЛОГИКА: Анализ кэшбэка ===========
        if args.analyze_cashback:
            run_cashback_analysis(args)
            return  # Завершаем выполнение после анализа кэшбэка
        # ===================================================

        # Получаем путь к корневой папке проекта (на уровень выше src)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger.info(f"Корневая папка проекта: {root_dir}")

        # Формируем базовый путь к файлу Excel
        excel_path = os.path.join(root_dir, 'data', 'operations.xlsx')

        # Формируем базовый путь к файлу настроек
        settings_path = os.path.join(root_dir, 'data', 'user_settings.json')

        # Если указан пользовательский путь к Excel, используем его
        if args.excel_path:
            excel_path = args.excel_path
            logger.info(f"Используем пользовательский путь к Excel: {excel_path}")
        else:
            logger.info(f"Используем путь к Excel по умолчанию: {excel_path}")

        # Если указан пользовательский путь к настройкам
        if args.settings_path:
            settings_path = args.settings_path
            logger.info(f"Используем пользовательский путь к настройкам: {settings_path}")
        else:
            logger.info(f"Используем путь к настройкам по умолчанию: {settings_path}")

        # Проверяем существование файлов
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Файл Excel не найден: {excel_path}")

        if not os.path.exists(settings_path):
            raise FileNotFoundError(f"Файл настроек не найден: {settings_path}")

        # Определяем дату
        current_datetime = datetime.strptime(args.date, '%Y-%m-%d %H:%M:%S')
        logger.info(f"Используем дату: {current_datetime}")

        # Получаем данные для главной страницы
        logger.info("Начинаем получение данных для главной страницы...")
        result = get_main_page_data(
            date_str=current_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            excel_path=excel_path
        )

        # ВАЖНОЕ ИСПРАВЛЕНИЕ: Корректируем данные перед выводом
        if result and isinstance(result, dict):
            # 1. Исправляем отрицательные значения кэшбэка
            if 'cards' in result:
                for card in result['cards']:
                    # Делаем кэшбэк положительным (он всегда должен быть положительным)
                    if 'cashback' in card and card['cashback'] < 0:
                        card['cashback'] = abs(card['cashback'])

                    # Округляем до 2 знаков после запятой
                    if 'cashback' in card:
                        card['cashback'] = round(card['cashback'], 2)

                    # Если card_number пустой, ставим "Не указана" или маску
                    if 'card_number' in card and not card['card_number'].strip():
                        card['card_number'] = "*XXXX"

            # 2. Удаляем дубликаты транзакций
            if 'top_transactions' in result and len(result['top_transactions']) > 1:
                # Создаем список уникальных транзакций
                seen = set()
                unique_transactions = []
                for transaction in result['top_transactions']:
                    # Создаем ключ для проверки уникальности
                    key = (
                        transaction.get('date', ''),
                        transaction.get('amount', 0),
                        transaction.get('category', ''),
                        transaction.get('description', ''),
                        transaction.get('card_number', '')
                    )
                    if key not in seen:
                        seen.add(key)
                        unique_transactions.append(transaction)

                # Ограничиваем топ-транзакции (например, 5 штук)
                result['top_transactions'] = unique_transactions[:5]

            # 3. Округляем значения валютных курсов и цен акций
            if 'currency_rates' in result:
                for rate in result['currency_rates']:
                    if 'rate' in rate:
                        rate['rate'] = round(rate['rate'], 4)

            if 'stock_prices' in result:
                for stock in result['stock_prices']:
                    if 'price' in stock:
                        stock['price'] = round(stock['price'], 2)

        # ГАРАНТИРОВАННЫЙ ВЫВОД - СИНХРОННЫЙ
        print("\n" + "=" * 80)
        print("РЕЗУЛЬТАТ РАБОТЫ ПРИЛОЖЕНИЯ (JSON):")
        print("=" * 80)

        # Принудительно сбрасываем буфер вывода
        sys.stdout.flush()

        try:
            # Преобразуем результат в JSON с настройками для чисел
            class DecimalEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, float):
                        # Округляем все float до 2 знаков
                        return round(obj, 2)
                    return super().default(obj)

            json_output = json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                cls=DecimalEncoder
            )

            # Выводим результат
            print(json_output)

            # Также записываем в файл для гарантии
            output_file = os.path.join(root_dir, 'output_result.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)

            print(f"\n✅ Результат также сохранен в: {output_file}")

        except Exception as json_error:
            print(f"❌ Ошибка при формировании JSON: {str(json_error)}")
            print(f"📄 Сырые данные: {result}")

            # Записываем сырые данные
            output_file = os.path.join(root_dir, 'output_raw.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(str(result))

        print("\n" + "=" * 80)
        print("ПРИЛОЖЕНИЕ ЗАВЕРШИЛО РАБОТУ")
        print("=" * 80)

        logger.info("Приложение завершило работу успешно")

    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {str(e)}")
        print(f"Ошибка: {str(e)}")
        print("\nПроверьте наличие следующих файлов:")
        print("1. operations.xlsx в папке data/")
        print("2. user_settings.json в папке data/")
        print("3. .env файл с API ключами (опционально)")
        exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        print(f"Произошла ошибка: {str(e)}")
        exit(1)


if __name__ == "__main__":
    # Принудительная настройка вывода
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
