#!/usr/bin/env python
"""
Генератор cpp файлов
"""
import cparser_lite as cpplite
import asp_db_cpp as aspdb


def get_table_define(table_name):
    """
    Получить дефайн по имени таблицы

    :param table_name: Имя таблицы
    :return: Дефайн таблицы
    """
    return table_name.upper() + '_TABLE'


def get_table_enum(table_name):
    """
    Получить enum по имени таблицы

    :param table_name: Имя таблицы
    :return: enum таблицы
    """
    return 'table_' + table_name.lower()


def get_table_fields(table_name):
    return table_name + '_fields'


def get_table_unique(table_name):
    return table_name + '_unique'


def get_table_references(table_name):
    return table_name + '_references'


def get_create_setup(table_name):
    return table_name + '_create_setup'


# def get_field_define(field_name):
#     return field_name.upper()


def get_field_define(table_name, field_name):
    return get_table_define(table_name) + '_' + field_name.upper()


def get_table_flags(table_name):
    """
    Имя enum с флагами таблицы

    :param table_name:
    :return:
    """
    return 'flags_' + table_name


def get_field_flag(table_name, field_name):
    return 'f_' + table_name + '_' + field_name


class AspDBTableText:
    def __init__(self, cpp_struct):
        """
        Данные таблицы для записи в оригинальный с++ файл структур таблиц

        :param cpp_struct: AspDBCppStruct python имплементация хэддера
        """
        self.cpp_struct = cpp_struct
        self.flags_enum = self.init_enum()

    def init_enum(self):
        """
        Инициализировать enum файлов

        :return: CppEnum с соответствующими флагами полей
        """
        # fields
        flags = cpplite.CppEnum(get_table_flags(self.cpp_struct.get_name()))
        for i, field in enumerate(self.cpp_struct.fields):
            if not flags.try_add_field(get_field_flag(self.cpp_struct.get_name(), field.get_name()), pow(2, i)):
                raise BaseException('Error append flags enum for struct ' + self.cpp_struct.name)
        fields_count = len(self.cpp_struct.fields)
        # refs
        for j, ref in enumerate(self.cpp_struct.foreign_refs):
            if not flags.try_add_field(get_field_flag(self.cpp_struct.get_name(),
                                                      ref.field.get_name()), pow(2, j + fields_count)):
                raise BaseException('Error append flags enum for struct ' + self.cpp_struct.name)
        fields_count += len(self.cpp_struct.foreign_refs)
        # добавить full и emtpy параметры
        flags.try_add_field('f_full', pow(2, fields_count) - 1)
        flags.try_add_field('f_empty', 0)
        return flags

    def enum_as_text(self):
        """
        Получить тестовое представление перечисления

        :return: Текстовое представление enum
        """
        et = 'enum ' + self.flags_enum.name + ' {\n'
        if len(self.flags_enum.fields) > 0:
            et += '  ' + self.flags_enum.fields[0][0] + ' = ' + format(self.flags_enum.fields[0][1], '#06x')
            for field in self.flags_enum.fields[1:]:
                et += ',\n  ' + field[0] + " = " + format(field[1], '#06x')
        et += '\n};\n'
        return et


class AspDBTablesGenerator:
    """
    Инкапсулированный функционал генерации .cpp файлов
    """

    def __init__(self, header_file, module_name=''):
        """
        Инициализировать данные таблиц

        :param header_file: CPP хэдер со структурами данных
        """
        self.header_file = header_file
        self.files_suffix = '_auto'
        self.asp_db_interface = 'IDBTables'
        # собственные имена структур/таблиц
        self.tables = list()
        # имя модуля набора таблиц
        self.db_tables_ns = ''
        # имя enum таблиц
        self.db_tables_enum = ''
        # имя реализующего интерфейс IDBTables класса таблиц
        self.db_tables_class = ''
        if not module_name:
            self.module_name = header_file[: header_file.find('.')]
        else:
            self.module_name = module_name
        self.asp_tables = None
        with open(self.header_file, 'r') as f:
            self.asp_tables = aspdb.AspDBCppFile(f.read())

    def get_file_module_name(self):
        return self.module_name + self.files_suffix

    def generate_files(self):
        if self.asp_tables:
            self.asp_tables.init_structs()
            self.set_class_name()
            self.tables = self.init_tables()
            # self.update_original_header()
            self.init_tables_header()
            self.init_tables_source()

    def update_original_header(self):
        """
        Обновить хэддер с оригинальными таблицами. Enum прописать, сэттеры

        :return:
        """
        raise Exception

    def init_tables(self):
        """
        Инициализировать данные таблиц

        :return:
        """
        tables = list()
        if self.asp_tables:
            for i, struct in enumerate(self.asp_tables.cpp_structs):
                tables.append(struct.name)
        return tables

    def set_class_name(self):
        """
        Установить имя класса, наследующего от IDBTables

        :return:
        """
        self.db_tables_ns = self.module_name
        self.db_tables_ns = self.db_tables_ns.lower()
        self.db_tables_enum = self.db_tables_ns + '_tables'
        # класс наследник IDBTables
        self.db_tables_class = self.db_tables_ns[:1].upper() +\
                               self.db_tables_ns[1:].lower() + self.asp_db_interface[1:]

    def init_tables_header(self):
        """
        Инициализировать хэддер-файл таблиц

        :return: Nothing
        """
        # добавить дефайны
        text = '#ifndef ' + self.module_name.upper() + '_GUARD_H\n'
        text += '#define ' + self.module_name.upper() + '_GUARD_H\n\n'
        text += self.add_defines_h()
        text += self.add_flags_enums()
        text += self.add_data_structs_h()
        text += self.add_template_specification_h()
        text += '#endif  // !' + self.module_name.upper() + '_GUARD_H\n'
        with open(self.get_file_module_name() + '.h', 'w') as f:
            f.write(text)

    def add_defines_h(self):
        """
        Добавить дефайны таблиц и полей таблиц

        :return: cpp код
        """
        # общая текстовая строка
        text = ''
        # строка имён полей
        field_names = ''
        if self.asp_tables:
            for i, struct in enumerate(self.asp_tables.cpp_structs):
                table = struct.name.upper()
                text += '\n/* table: ' + table + ' */\n'
                for j, field in enumerate(struct.fields):
                    # добавим дефайн на поле таблицы
                    text += '#define ' + get_field_define(table, field.get_name()) +\
                            ' (' + get_table_define(table) + ' | ' + format(j + 1, '#06x') + ')\n'
                    field_names += '#define ' + get_field_define(table, field.get_name()) +\
                                   '_NAME' + ' ' + '"' + field.get_name().lower() + '"\n'
                fields_count = len(struct.fields)
                for k, ref in enumerate(struct.foreign_refs):
                    text += '#define ' + get_field_define(table, ref.field.get_name()) + \
                            ' (' + get_table_define(table) + ' | ' + format(k + 1 + fields_count, '#06x') + ')\n'
                    field_names += '#define ' + get_field_define(table, ref.field.get_name()) + \
                                   '_NAME' + ' ' + '"' + ref.field.get_name().lower() + '"\n'
            tables_defs = ''
            for i, table in enumerate(self.tables):
                tables_defs += '#define ' + get_table_define(table) + ' ' +\
                               format((i + 1) * pow(2, 16), '#010x') + '\n'
            text = tables_defs + '\n' + text
            text += '\n' + field_names + '\n'
        return text

    def add_flags_enums(self):
        """
        Добавить enum с флагами
        :return:
        """
        text = '\n'
        for struct in self.asp_tables.cpp_structs:
            text += AspDBTableText(struct).enum_as_text()
        return text

    def add_data_structs_h(self):
        """
        Добавить enum и класс-наследник IDBTables

        :return: cpp код
        """
        text = '\n'
        # enum таблиц
        text += 'enum ' + self.db_tables_enum + ' {\n'
        text += '  table_undefined = UNDEFINED_TABLE'
        for i, table in enumerate(self.tables):
            text += ',\n' + '  ' + get_table_enum(table) + ' = ' + get_table_define(table) + ' >> 16'
        text += '\n};\n\n'
        text += 'class ' + self.db_tables_class + ' final: public ' + self.asp_db_interface + ' {\n'
        text += '  std::string GetTableName(db_table t) const override;\n'
        text += '  const db_fields_collection *GetFieldsCollection(db_table t) const override;\n'
        text += '  db_table StrToTableCode(const std::string &tname) const override;\n'
        text += '  std::string GetIdColumnName(db_table dt) const override;\n'
        text += '  const db_table_create_setup &CreateSetupByCode(db_table dt) const override;\n'
        text += '};\n'
        return text

    def add_template_specification_h(self):
        """
        Добавить специализацию шаблонов
        :return:
        """
        text = '\n/* GetTableName */\n'
        for table in self.tables:
            text += 'template<>\n' \
                    'std::string ' + self.asp_db_interface + '::GetTableName<' + table + '>() const;\n'
        text += '\n/* GetTableCode */\n'
        for table in self.tables:
            text += 'template<>\n' \
                    'db_table ' + self.asp_db_interface + '::GetTableCode<' + table + '>() const;\n'
        text += '\n/* setInsertValues */\n'
        for table in self.tables:
            text += 'template<>\n' \
                    'void ' + self.asp_db_interface + '::setInsertValues<' + table + '>(\n' \
                    '    db_query_insert_setup *src, const ' + table + ' &select_data) const;\n'
        text += '\n/* SetSelectData */\n'
        for table in self.tables:
            text += 'template<>\n' \
                    'void ' + self.asp_db_interface + '::SetSelectData<' + table + '>(\n' \
                    '    db_query_select_result *src, std::vector<' + table + '> *out_vec) const;\n'
        return text + '\n'

    def init_tables_source(self):
        """
        Инициализировать cpp файл таблиц

        :return:
        """
        text = '#include ' + self.module_name + '.h\n\n'
        text += '#include ' + self.header_file + '\n'
        text += '#include "db_connection_manager.h"\n\n'
        text += '#include <map>\n'
        text += '#include <memory>\n\n\n'
        text += self.add_str_tables()
        for struct in self.asp_tables.cpp_structs:
            text += self.add_table_fields(struct)
        text += self.add_get_field_collection()
        text += self.add_get_id_colname()
        text += self.add_create_setup()
        text += self.add_get_table_name()
        text += self.add_get_table_code()
        text += self.add_field2str_functions()
        text += self.add_str2field_functions()
        text += self.add_set_insert_values()
        text += self.add_set_select_data()
        with open(self.get_file_module_name() + '.cpp', 'w') as f:
            f.write(text)

    def add_get_field_collection(self):
        text = '\nconst db_fields_collection *' + self.db_tables_class + '::GetFieldsCollection(db_table dt) const {\n'
        text += '  const db_fields_collection *result = nullptr;\n'
        text += '  switch(dt) {\n'
        for struct in self.asp_tables.cpp_structs:
            text += '    case ' + get_table_enum(struct.get_name()) + ':\n'
            text += '      result = &' + get_table_fields(struct.get_name()) + ';\n'
            text += '      break;\n'
        text += '    case table_undefined:\n'
        text += '    default:\n'
        text += '      throw DBException(ERROR_DB_TABLE_EXISTS, "Неизвестный код таблицы");\n'
        text += '  }\n'
        text += '  return result;\n'
        text += '}\n'
        return text

    def add_get_id_colname(self):
        """
        Прописать функцию возвращающую имя столбца хранящего id таблицы

        :return: cpp код метода GetIdColumnName
        """
        text = '\n'
        text += 'std::string ' + self.db_tables_class + '::GetIdColumnName(db_table dt) const {\n'
        text += '  std::string name = "";\n'
        text += '  switch (dt) {\n'
        for struct in self.asp_tables.cpp_structs:
            fields = [f.get_name() for f in struct.fields]
            if 'id' in fields:
                text += '    case ' + get_table_enum(struct.get_name()) + ':\n'
                text += '      name = TABLE_FIELD_NAME(' + get_field_define(struct.get_name(), 'id') + ');\n'
                text += '      break;\n'

        text += '    case default: break;\n'
        text += '  }\n'
        text += '  return name;\n'
        text += '}\n'
        return text

    def add_create_setup(self):
        """
        Прописать функцию возвращающую сетап создания таблицы `CreateSetupByCode`

        :return: cpp код метода CreateSetupByCode
        """
        text = 'const db_table_create_setup &' + self.db_tables_class + '::CreateSetupByCode(db_table dt) const {\n'
        text += '  switch (dt) {\n'
        for struct in self.asp_tables.cpp_structs:
            text += '    case ' + get_table_enum(struct.get_name()) + ':\n'
            text += '      return ' + get_create_setup(struct.get_name()) + ';\n'
        text += '    case table_undefined:\n'
        text += '    default:\n'
        text += '      throw DBException(ERROR_DB_TABLE_EXISTS, "Undefined table");\n'
        text += '  }\n'
        text += '}\n'
        return text

    def add_get_table_name(self):
        """
        Прописать перегруженные шаблоны функций возвращающих имя таблицы

        :return: cpp код методов template<> IDBTables::GetTableName
        """
        text = '\n'
        for struct in self.asp_tables.cpp_structs:
            text += 'template <>\n'
            text += 'std::string IDBTables::GetTableName<' + struct.get_name() + '>() const {\n'
            text += '  auto x = str_tables.find(' + get_table_enum(struct.get_name()) + ');\n'
            text += '  return (x != str_tables.end()) ? x->second : "";\n'
            text += '}\n'
        return text

    def add_get_table_code(self):
        """
        Прописать перегруженные шаблоны методы возвращающие код таблицы

        :return: cpp код методов template<> IDBTables::GetTableCode
        """
        text = '\n'
        for struct in self.asp_tables.cpp_structs:
            text += 'template <>\n'
            text += 'db_table IDBTables::GetTableCode<' + struct.get_name() + '>() const {\n'
            text += '  return ' + get_table_enum(struct.get_name()) + ';\n'
            text += '}\n'
        return text

    def add_field2str_functions(self):
        """
        Собрать функции преобразования полей таблиц к их строковым
        представлениям.
        Дефолтные прокидфваются на шаблонную функцию `field2str(const T &)`.
        Для особых полей особые обработчики, зарегистрированные в хэддере
        конфигурации таблицы.

        :return: cpp код
        """
        text = '\n'
        for struct in self.asp_tables.cpp_structs:
            default_case = ''
            cp_case = ''
            text += 'std::string field2str_' + struct.get_name() + '(' + get_table_flags(struct.get_name()) + \
                    ' flag, const ' + struct.get_name() + ' &select_data) const {\n'
            text += '  std::string result;\n'
            text += '  switch (flag) {\n'
            for field in struct.fields:
                case = self.get_field2str_text(struct.get_name(), field)
                cp_case += case[0]
                default_case += case[1]
            for ref in struct.foreign_refs:
                case = self.get_field2str_text(struct.get_name(), ref.field)
                cp_case += case[0]
                default_case += case[1]
            text += cp_case
            text += default_case
            text += '    default:\n'
            text += '      result = field2str(select_data);\n'
            text += '  }\n'
            text += 'return result;\n'
            text += '}\n'
        return text

    def get_field2str_text(self, table_name, field):
        """
        Получить текстовое представление функции конвертации поля к строке

        :return:
        """
        cp_case = ''
        default_case = ''
        if field.to_str:
            # особая обработка
            cp_case = '    case ' + get_field_flag(table_name, field.get_name()) + ':\n'
            cp_case += '      result = ' + field.to_str + '(select_data);\n'
            cp_case += '      break;\n'
        else:
            # прокинуть на дефолтную обработку
            default_case = '    case ' + get_field_flag(table_name, field.get_name()) + ':\n'
        return [cp_case, default_case]

    def add_str2field_functions(self):
        """
        Функция обратная `add_field2str_functions` - строки конвертирует в поля
        """
        raise Exception

    def add_set_insert_values(self):
        """
        Прописать перегруженные шаблоны методы заполняющие сетап добавления

        :return:
        """
        text = '\n'
        for struct in self.asp_tables.cpp_structs:
            text += 'template <>\n'
            text += 'void IDBTables::setInsertValues<' + get_table_enum(struct.get_name()) +\
                    '>(db_query_insert_setup *src,\n'
            text += '    const ' + struct.get_name() + ' &select_data) const {\n'
            text += '  if (select_data.initialized == 0x00)\n'
            text += '    return;\n'
            text += '  db_query_basesetup::row_values values;\n'
            text += '  db_query_basesetup::field_index i;\n'
            for field in struct.fields:
                text += '  insert_macro(' + get_field_flag(struct.get_name(), field.get_name()) + ', ' +\
                        get_field_define(struct.get_name(), field.get_name()) + ', field2str_' + struct.get_name() +\
                        '(' + get_field_flag(struct.get_name(), field.get_name()) + ', select_data));\n'
            for ref in struct.foreign_refs:
                text += '  insert_macro(' + get_field_flag(struct.get_name(), ref.field.get_name()) + ', ' + \
                        get_field_define(struct.get_name(), ref.field.get_name()) + ', field2str_' + struct.get_name() + \
                        '(' + get_field_flag(struct.get_name(), ref.field.get_name()) + ', select_data));\n'
            text += '  src->values_vec.emplace_back(values);\n'
            text += '}\n'
        return text

    def add_set_select_data(self):
        """
        Добавить спецификации шаблонных методов `SetSelectData`

        :return: cpp код
        """
        text = '\n'
        for struct in self.asp_tables.cpp_structs:
            text += 'template<>\n'
            # TODO: ??? да почему опять вектор-то, а не итераторы??
            #   хотя здесь терпимо
            text += 'void IDBTables::SetSelectData<' + struct.get_name() + '>(db_query_select_result *src,\n' +\
                    '    std::vector<' + struct.get_name() + '> *out_vec) const {\n'
            text += '  for (auto &row: src->values) {\n'
            # TODO: тут дефолтный конструктор ттаблицы БД - не гибко
            text += '    ' + struct.get_name() + ' tmp;\n'
            text += '    for (auto &col: row) {\n'
            text += '      if (0) {/*(sorry)*/\n'
            for field in struct.fields:
                text += '      } else if {\n'
                text += '        select_macro(' + get_field_flag(struct.get_name(), field.get_name()) + ', ' + \
                        get_field_define(struct.get_name(), field.get_name()) + ', str2field_' + struct.get_name() + \
                        '(' + get_field_flag(struct.get_name(), field.get_name()) + ', col.second));\n'
            for ref in struct.foreign_refs:
                text += '      } else if {\n'
                text += '        select_macro(' + get_field_flag(struct.get_name(), ref.field.get_name()) + ', ' + \
                        get_field_define(struct.get_name(), ref.field.get_name()) + ', str2field_' + \
                        struct.get_name() + '(' + get_field_flag(struct.get_name(), ref.field.get_name()) + \
                        ', col.second));\n'
            # закрывающая скобка на последний `else if`
            text += '      }\n'
            text += '    }\n'
            text += '    if (tmp.initialized != ' + get_table_flags(struct.get_name()) + '::f_empty)\n'
            text += '      out_vec->push_back(std::move(tmp));\n'
            text += '  }\n'
            text += '}\n'

    def add_str_tables(self):
        text = 'static std::map<db_table, std::string> str_tables = {\n'
        for table in self.tables:
            text += '  {' + get_table_enum(table) + ', "' + table + '"},\n'
        text += '};\n\n'
        # GetTableName
        text += 'std::string ' + self.db_tables_class + '::GetTableName(db_table t) const {\n'
        text += '  auto x = str_tables.find(t);\n'
        text += '  return (x != str_tables.end()) ? x->second: "";\n'
        text += '}\n\n'
        # StrToTableCode
        text += 'db_table ' + self.db_tables_class + '::StrToTableCode(const std::string &tname) const {\n'
        text += '  for (const auto &x: str_tables)\n'
        text += '    if (x.second == tname)\n'
        text += '      return x.first;\n'
        text += '  return table_undefined;\n'
        text += '}\n'
        return text

    def add_table_fields(self, struct):
        # fields collection
        fields_name = struct.get_name() + '_fields'
        text = '\nconst db_fields_collection ' + fields_name + ' = {\n'
        for field in struct.fields:
            text += self.add_field_string(struct.get_name(), field)
        for ref in struct.foreign_refs:
            text += self.add_field_string(struct.get_name(), ref.field)
        text += '};\n'

        # unique
        unique_name = struct.get_name() + '_uniques'
        unique_str = 'static const db_table_create_setup::uniques_container ' + \
                     unique_name + ' = {'
        if struct.unique:
            unique_str += '\n  {{ '
            for field in struct.fields:
                unique_str += ' TABLE_FIELD_NAME(' + get_field_define(struct.get_name(), field.get_name()) + '),\n'
            unique_str += '}}\n'
        text += '\n' + unique_str + '};\n'

        # references
        ref_name = struct.name + '_references'
        if struct.foreign_refs:
            ref_str = 'static const std::shared_ptr<db_ref_collection> ' + ref_name + '(\n    new db_ref_collection {'
            for ref in struct.foreign_refs:
                ref_str += '\n    db_reference(TABLE_FIELD_NAME(' + ref.field.get_name() + '), ' + ref.ref.get_ftable() +\
                           ',\n        ' + ref.ref.get_ftable_pk() + ', true, ' + aspdb.ref_act_type(ref.ref.get_update_act()) +\
                           ',\n        ' + aspdb.ref_act_type(ref.ref.get_delete_act()) + '),'
            ref_str += '});\n'
            text += ref_str

        text += '\n'
        # create_setup
        create_setup = 'static const db_table_create_setup ' + get_create_setup(struct.get_name()) + '(\n'
        create_setup += '    ' + get_table_enum(struct.name) + ', ' + fields_name + ',\n    ' + unique_name + ', '
        create_setup += ref_name if struct.foreign_refs else 'nullptr'
        create_setup += ');\n'

        return text + create_setup

    def add_field_string(self, table_name, field):
        text = '  db_variable(TABLE_FIELD_PAIR(' + get_field_define(table_name, field.get_name()) \
               + '), ' + field.asp_type + ',\n'
        flags = '  {' + field.get_flags_str()
        flags += '}'
        text += flags + '\n'
        return text
