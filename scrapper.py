import requests
import re
from bs4 import BeautifulSoup
import json
import os

class ProductScraper:
    def __init__(self, url):
        self.url = url
        self.soup = None
        self.product_type = None
        self.title = ''
        self.price = 0.0

    def fetch_page(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(self.url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f'Ошибка при запросе: {response.status_code}')
        
        self.soup = BeautifulSoup(response.text, 'html.parser')

    def parse_product_info(self):
        try:
            self.title = self.soup.find('div', class_='heading').get_text(strip=True)
            price_text = self.soup.find('div', class_='spec-about__price').get_text(strip=True).split(' –')[0]
            self.price = float(price_text.replace(',', '.').replace(' ', ''))
        except AttributeError:
            raise Exception('Не удалось найти необходимые элементы на странице.')

    def parse_tables(self):
        tables_container = self.soup.find('div', class_='spec-info__main')
        
        if not tables_container:
            raise Exception('Контейнер с таблицами не найден.')
        
        tables = tables_container.find_all('table')
        
        if not tables:
            raise Exception('Таблицы не найдены.')

        combined_data = {}
        field_mapping = self.get_field_mapping()

        for table in tables:
            table_data = self.extract_table_data(table)
            self.process_table_data(table_data, combined_data, field_mapping)

        return combined_data

    def extract_table_data(self, table):
        return [
            [col.get_text(strip=True) for col in row.find_all(['td', 'th'])]
            for row in table.find_all('tr')
            if row.find_all(['td', 'th'])
        ]

    def process_table_data(self, table_data, combined_data, field_mapping):
        measurement_units = self.get_measurement_units()

        for row in table_data:
            if len(row) >= 2 and row[0] in field_mapping[self.product_type]:
                new_key = field_mapping[self.product_type][row[0]]
                value = row[1].strip()
                combined_data[new_key] = self.parse_value(value, measurement_units)

    def parse_value(self, value, measurement_units):
        value = value.replace("Micro-ATX", "mATX").replace("microATX", "mATX")
        
        if value == '+':
            return True
        elif value == '-':
            return False
        elif all(char.isdigit() or char.isspace() or char == '.' for char in value):
            numeric_value = float(value.replace(' ', '').replace(',', '.'))
            return int(numeric_value) if numeric_value.is_integer() else numeric_value
        elif any(unit in value for unit in measurement_units):
            numeric_value = re.sub(r'[^0-9.,]', '', value)
            if numeric_value:
                numeric_value = numeric_value.replace(',', '.')
                numeric_value = float(numeric_value)
                return int(numeric_value) if numeric_value.is_integer() else numeric_value
            return value
        else:
            return value
    
    def get_field_mapping(self):
        return {
            'cpu': {
                '?Сокет': 'socket',
                'Год выхода на рынок': 'release_year',
                '?Количество ядер': 'core_count',
                'Количество потоков': 'thread_count',
                '?Техпроцесс': 'process_technology',
                '?Частота процессора': 'processor_clock',
                '?Объем кэша L2': 'l2_cache_size',
                '?Объем кэша L3': 'l3_cache_size',
                '?Тепловыделение': 'tdp',
                'Тип памяти': 'memory_type',
                '?Интегрированное графическое ядро': 'integrated_graphics',
                '?Название графического ядра': 'integrated_graphics_name',
                '?Максимальная частота графического ядра': 'integrated_graphics_freq',
            },
            'motherboard': {
                '?Socket': 'socket',
                '?Тип': 'memory_type',
                '?Макс. объем': 'max_memory',
                '?Количество слотов': 'memory_slots',
                '?Максимальная': 'max_memory_frequency',
                '?Двухканальный': 'dual_channel',
                '?Название': 'chipset_name',
                '?Поддержка UEFI': 'uefi_support',
                '?Общее количество разъемов SATA': 'sata_slots',
                '?Количество слотов M.2': 'm2_slots',
                '?Количество разъемов USB': 'usb_ports_total',
                '?Основной разъем питания': 'main_power_connector',
                '?Разъем питания процессора': 'cpu_power_connector',
                '?Форм-фактор': 'form_factor',
            },
            'gpu': {
                '?Тип подключения': 'connection_type',
                'Кодовое название': 'video_processor',
                '?Производитель': 'manufacturer',
                '?Тип памяти': 'memory_type',
                '?Объем памяти': 'memory_size',
                '?Частота памяти': 'memory_frequency',
                'Трассировка лучей': 'ray_tracing',
                '?Версия DirectX': 'directx_version',
                '?Версия OpenGL': 'opengl_version',
                '?Необходимость дополнительного питания': 'additional_power_required',
                '?Разъем дополнительного питания': 'additional_power_connector',
                '?Рекомендуемая мощность блока питания': 'recommended_psu',
                'Ширина': 'width',
            },
            'hdd': {
                '?Объем жесткого диска': 'capacity',
                '?Форм-фактор': 'form_factor',
                '?Скорость записи': 'write_speed',
                '?Скорость чтения': 'read_speed',
                '?Скорость вращения': 'rpm'
            },
            'ssd': {
                '?Объем': 'capacity',
                '?Форм-фактор': 'form_factor',
                '?Скорость записи': 'write_speed',
                '?Скорость чтения': 'read_speed',
                '?Тип PCI-E': 'pci_e_type'
            },
            'case': {
                'Форм-фактор': 'motherboard_format',
                'Макс. размер материнской платы': 'max_motherboard_size',
                '?Цвет корпуса': 'case_color',
                '?Материал корпуса': 'case_material',
                '?Наличие окна на боковой стенке': 'side_window',
                'Материал окна': 'window_material',
                '?Максимальная высота процессорного кулера': 'max_cpu_cooler_height',
                '?Максимальная длина видеокарты': 'max_gpu_length',
                'Макс. длина блока питания': 'max_psu_length',
                '?Возможность установки системы жидкостного охлаждения': 'liquid_cooling_support'
            },
            'cooler': {
                'Сокет': 'supported_sockets',
                '?Водяное охлаждение': 'liquid_cooling',
                '?Максимальная рассеиваемая мощность': 'tdp'
            },
            'ram': {
                '?Тип': 'type',
                '?Объем одного модуля': 'module_capacity',
                '?Количество модулей': 'module_count',
                '?Тактовая частота': 'clock_frequency',
                '?Радиатор': 'heat_spreader',
                '?Поддержка XMP': 'xmp_support'
            },
            'psu': {
                '?Форм-фактор': 'form_factor',
                '?Мощность': 'power',
                '?Ширина': 'width',
                '?Высота': 'height',
                '?Глубина': 'depth',
                '?Вес': 'weight'
            }
        }

    def get_measurement_units(self):
        return [
            'Мб/с', 'Мб', 'Гб', 'Тб', 'ч', 'нм', 'МГц', 'Вт', 'мм', 'rpm'
        ]

    def save_to_json(self, data):
        os.makedirs('res', exist_ok=True)
        filename = f'res/{self.product_type}_{self.title.lower().replace(" ", "_").replace("/", "")}.json'
        with open(filename, 'w', encoding='windows-1251') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        print(f'Данные успешно сохранены в {filename}')

    def determine_type_from_url(self):
        if 'utility-cpu' in self.url:
            self.product_type = 'cpu'
        elif 'utility-motherboards' in self.url:
            self.product_type = 'motherboard'
        elif 'utility-graphicscards' in self.url:
            self.product_type = 'gpu'
        elif 'utility-harddisks' in self.url:
            self.product_type = 'hdd'
        elif 'utility-ssd' in self.url:
            self.product_type = 'ssd'
        elif 'utility-cases' in self.url:
            self.product_type = 'case'
        elif 'utility-cooling' in self.url:
            self.product_type = 'cooler'
        elif 'utility-memory' in self.url:
            self.product_type = 'ram'
        elif 'utility-powermodules' in self.url:
            self.product_type = 'psu'
        else:
            self.product_type = 'unknown'
        
    def parse_product_and_tables(self):
        try:
            self.determine_type_from_url()
            self.fetch_page()
            self.parse_product_info()
            tables = self.parse_tables()

            img_tags = self.soup.find_all('img', class_='spec-images__img')
            img_urls = [img['src'] for img in img_tags if img.get('src')]

            self.title = re.sub(r'(Процессор |Материнская плата |Видеокарта |Жесткий диск |SSD диск |Корпус для компьютера |Кулер для процессора |Модуль памяти |Блок питания )\s*', '', self.title).strip()

            result = {
                'type': self.product_type,
                'title': self.title,
                'price': self.price,
                'image_urls': img_urls,
                'data': tables
            }

            self.save_to_json(result)

        except Exception as e:
            print(e)


if __name__ == '__main__':
    while True:
        user_input = input('Введите ссылку (exit для выхода): ')
        if user_input.lower() == "exit":
            break
        else:
            scraper = ProductScraper(user_input)
            scraper.parse_product_and_tables()