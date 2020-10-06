"""
Модуль обработки конфигурации cpp хэдера asp_db
"""
import cparser_lite as cpplite
import re
from enum import Enum


class AspDBCppFunctions(cpplite.ICppFunctions):
    """
    Класс инкапсулирующий функционал инициализации данных AspDB
    """
    def init_cpp_structs(self, name, source):
        return AspDBCppStructs(name, source)


class AspDBField:
    """
    Структура описывающая поля таблиц ASP_TABLE
    """
    def __init__(self, asp_type, asp_name, asp_args):
        """
        Инициализировать поле таблицы

        :param asp_type: Тип поля
        :param asp_name: Имя поля
        :param asp_args: Массив аргументов
        """
        self.asp_type = asp_type
        self.asp_name = asp_name
        self.asp_args = [x.strip().upper() for x in asp_args.split(',')]
        # флаги полей
        self.not_null = False
        self.is_array = False
        self.is_primary_key = False
        self.is_reference = False

        self.parse_arguments()

    def parse_arguments(self):
        if 'NOT_NULL' in self.asp_args:
            self.not_null = True
        if 'ARRAY' in self.asp_args:
            self.is_array = True

    def get_name(self):
        return self.asp_name


class AspDBRefAction(Enum):
    """
    Перечисление действий со ссылочными типами
    """
    # no act
    NON = 0
    # cascade
    CASCADE = 1
    # restrict
    RESTRICT = 2
    # set null
    SET_NULL = 3


def set_ref_action(act):
    """
    Получить код действия со ссылкой

    :param act: Строковое представление действия со ссылкой
    :return: Возвращает соответствующий enum
    """
    if act.upper() == 'CASCADE':
        return AspDBRefAction.CASCADE
    elif act.upper() == 'RESTRICT':
        return AspDBRefAction.RESTRICT
    elif act.upper() == 'SET NULL':
        return AspDBRefAction.SET_NULL
    return AspDBRefAction.NON


def ref_act_type(act):
    """
    Получить строковое представление типа действия

    :param act: Enum действия
    :return:
    """
    if type(act) != AspDBRefAction:
        raise BaseException('Несоответсвующий тип для восстанавления типа '
                            '`AspDBRefAction`: ' + str(type(act)))
    if act == AspDBRefAction.CASCADE:
        return 'db_reference_act::ref_act_cascade'
    elif act == AspDBRefAction.RESTRICT:
        return 'db_reference_act::ref_act_restrict'
    elif act == AspDBRefAction.SET_NULL:
        return 'db_reference_act::ref_act_set_null'
    else:
        return 'db_reference_act::ref_act_not'


class AspDBReference:
    """
    Структура внешнего ключа таблиц
    """
    def __init__(self, name, ftable_ref, on_update, on_delete):
        """
        Инициализировать ссылку

        :param name: Имя поля ссылки
        :param ftable_ref: Ссылка на поле внешней таблицы вида 'FTABLE(FTABLE_PK)'
        :param on_update: Update метод
        :param on_delete: Delete метод
        """
        self.name = name
        self.ftable, self.ftable_pk = self.init_fkey_ref(ftable_ref)
        self.on_update = set_ref_action(on_update)
        self.on_delete = set_ref_action(on_delete)

    def init_fkey_ref(self, ftable_ref):
        return ftable_ref[: ftable_ref.find('(')].strip(),\
               cpplite.get_brace_content(ftable_ref, '(', ')').strip()

    def get_ftable(self):
        return self.ftable

    def get_ftable_pk(self):
        return self.ftable_pk

    def get_update_act(self):
        return self.on_update

    def get_delete_act(self):
        return self.on_delete


class AspDBCppForeignData:
    """
    Класс данных внешней таблицы - имя, поле,
    """
    def __init__(self, field, ref):
        """
        Инициализировать объект данных ссылки на внешнюю таблицу

        :param field: Поле этой ссылки
        :param ref: Данные ссылки
        """
        self.field = field
        self.ref = ref


class AspDBCppStructs(cpplite.CppStructs):
    """
    Cpp структура таблицы в формате метатаблицы asp_db
    """
    def __init__(self, name, source):
        super(AspDBCppStructs, self).__init__(name, source)
        self.primary_key = list()
        self.foreign_refs = list()
        self.unique = list()
        # инициализировать данные
        self.init_data()
        try:
            # проверить валидность данных
            self.set_references_flags()
            self.check_data()
        except BaseException as e:
            print(e)

    def init_data(self):
        """
        Инициализировать данные
        :return:
        """
        # инициализировать поля
        self.fields = self.init_fields(r'field\s*\(')
        # инициализировать первичный ключ
        self.primary_key = self.init_primary_key()
        # инициализировать ссылки на другие таблицы
        self.foreign_refs = self.init_foreign_tables()
        # инициализировать уникальные комплексы
        self.unique = self.init_unique()

    def set_references_flags(self):
        """
        Установить флаги ссылок для полей

        :return:
        """
        ref_strs = [r.field.get_name() for r in self.foreign_refs]
        for f in self.fields:
            if f in ref_strs:
                f.is_reference = True

    def check_data(self):
        """
        Проверить списки первичного ключа, уникальных комплексов, ссылок

        :return: Nothing
        :raise: BaseException с описание проблемы
        """
        field_names = [f.get_name() for f in self.fields]
        for pk in self.primary_key:
            if pk not in field_names:
                raise BaseException('Несоответствующее имя поля первичного ключа: ' + pk)
        # TODO: в программе разделены ссылки и обычные поля, возможно стоит доработать
        #   момент с разбиением ссылки
        # for ref in self.foreign_refs:
        #     if ref.field.get_name() not in field_names:
        #         raise BaseException('Несоответствующее имя поля внешнего ключа: ' + ref.field.get_name())

    def init_fields(self, fields_pattern):
        """
        Инициализировать поля таблицы

        :param fields_pattern: Строковой паттерн поиска полей
        :return: Лист проинциализированных полей
        """
        fields = re.findall(fields_pattern, self.source)
        missed = []
        result_list = list()
        field_ind = -1
        for field in fields:
            field_ind = self.source.find(field, field_ind + 1)
            if field_ind == -1:
                missed.append(field + ' ~~ cannot find field in struct')
                continue
            content = cpplite.get_brace_content(self.source[field_ind:], '(', ')')
            params = content.split(',')
            # имя и тип
            try:
                result_list.append(AspDBField(params[0].strip(), params[1].strip(),
                                              params[2] if len(params) > 2 else ''))
            except IndexError as e:
                print('Error for parsing field type|name for ' + params[0])
        if len(missed) > 0:
            print('Warning: AspDBCppStruct.init_fields finished with errors')
            print(missed)
        return result_list

    def init_primary_key(self):
        """
        Инициализировать первичный ключ

        :TODO: может быть сложный первичный ключ с несколькими полями
        :return: Лист полей, в составе первичного ключа
        """
        pk_id = self.source.find('primary_key')
        pk = list()
        if pk_id != -1:
            pk_str = cpplite.get_brace_content(self.source[pk_id:], '(', ')').strip()
            pk = [f.strip() for f in pk_str.split(',')]
        return pk

    def init_foreign_tables(self):
        """
        Инициализировать ссылки на другие таблицы

        :return: Лист ссылок
        """
        # fields
        fkey_fields = self.init_fields(r'field_fkey\s*\(')
        # references
        references = self.init_references()
        # list of foreign_table_refs
        foreign_data = list()
        # check pairs fkey_field - reference
        for fkey_field in fkey_fields:
            # имя поля
            ffname = fkey_field.asp_name
            # нашлась соответствующая ссылка
            matched = False
            for ref in references:
                if ref.name == ffname:
                    foreign_data.append(AspDBCppForeignData(fkey_field, ref))
                    matched = True
                    break
            if not matched:
                print('Foreign data initialization error! No reference for ' + ffname)
        if len(fkey_fields) != len(references):
            print('Item count mismatch for `fkey_fields` and `references`')
        return foreign_data

    def init_references(self):
        """
        Инициализировать ссылки на другие таблицы

        :return: Список ссылок
        """
        refs = re.findall(r'reference\s*\(', self.source)
        ref_ind = -1
        result_list = list()
        missed = []
        for ref in refs:
            ref_ind = self.source.find(ref, ref_ind + 1)
            if ref_ind == -1:
                missed.append(ref + ' ~~ cannot find ref')
                continue
            ref_fields = cpplite.get_brace_content(self.source[ref_ind:], '(', ')').split(',')
            if len(ref_fields) < 3:
                missed.append(ref + ' ~~ cannot split ref')
                continue
            result_list.append(AspDBReference(ref_fields[0].strip(), ref_fields[1].strip(),
                                              ref_fields[2].strip(), ref_fields[3].strip()))
        if len(missed) > 0:
            print('Warning: AspDBCppStruct.init_references finished with errors')
            print(missed)
        return result_list

    def init_unique(self):
        """
        Инициализировать уникальный комплекс

        :return: Список уникальных полей
        :TODO: Комплекс уникальных значений может быть не один
        """
        unique_id = self.source.find('unique')
        unique = list()
        if unique_id != -1:
            unique_str = cpplite.get_brace_content(self.source[unique_id:], '(', ')')
            unique = [f.strip() for f in unique_str.split(',')]
        return unique


class AspDBCppFile(cpplite.CppFile):
    """
    Python инициализатор для модуля ASP_DB
    """
    def __init__(self, text):
        super(AspDBCppFile, self).__init__(text, AspDBCppFunctions())

    def get_class_marker(self):
        return 'ASP_TABLE'
