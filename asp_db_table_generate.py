#!/usr/bin/env python
"""
Генератор cpp файлов
"""
import cparser_lite as cpplite
import asp_db_cpp as aspdb


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
        flags = cpplite.CppEnum('flags_' + self.cpp_struct.name)
        for i, field in enumerate(self.cpp_struct.fields):
            if not flags.try_add_field('f_' + field.get_name(), pow(2, i)):
                raise BaseException('Error append flags enum for struct ' + self.cpp_struct.name)
        fields_count = len(self.cpp_struct.fields)
        # refs
        for j, ref in enumerate(self.cpp_struct.foreign_refs):
            if not flags.try_add_field('f_' + ref.field.get_name(), pow(2, j + fields_count)):
                raise BaseException('Error append flags enum for struct ' + self.cpp_struct.name)
        fields_count += len(self.cpp_struct.foreign_refs)
        # добавить full параметр
        flags.try_add_field('f_full', pow(2, fields_count) - 1)
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
        text += self.add_data_structs_h()
        text += self.add_template_specification_h()
        text += '#endif  //' + self.module_name.upper() + '_GUARD_H\n'
        with open(self.module_name + self.files_suffix + '.h', 'w') as f:
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
        text = self.add_str_tables()
        for struct in self.asp_tables.cpp_structs:
            text += self.add_table_fields(struct)
        text += self.add_get_field_collection()
        text += self.add_get_id_colname()
        with open(self.module_name + self.files_suffix + '.cpp', 'w') as f:
            f.write(text)

    def add_create_setup_funtions(self):
        # не нужны эти функции
        raise Exception

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
        text = 'std::string ' + self.db_tables_class + '::GetIdColumnName(db_table dt) const {\n'
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

    def add_str_tables(self):
        text = 'static std::map<db_table, std::string> str_tables = {\n'
        for table in self.tables:
            text += '  tables_pair(' + get_table_enum(table) + ', "' + table + '"),\n'
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
        text += '  return table_undefiend;\n'
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
        create_setup = 'static const db_table_create_setup ' + struct.name + '_create_setup(\n'
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
