import asp_db_table_generate as asp_db_tg
import asp_db_cpp
import unittest
import os

cpp_text = '#ifndef SOME_DEFINE' \
           '#define SOME_DEFINE' \
           '' \
           'struct ASP_TABLE test {' \
           '  field(integer, id, NOT_NULL);' \
           '  field(text, name, NOT_NULL);' \
           '' \
           '  primary_key(id)' \
           '};' \
           '' \
           'struct ASP_TABLE test2 {' \
           '  field(integer, id, NOT_NULL);' \
           '  field_fkey(bigint, fid);' \
           '  field_fkey(bigint, ffid);' \
           '' \
           '  primary_key(id, fid)' \
           '/* ссылка на первую таблицу */' \
           '  reference(fid, test(id), CASCADE, SET NULL)' \
           '/* ссылка на внешнюю таблицу */' \
           '  reference(ffid, ftest(id), CASCADE, CASCADE)' \
           '};' \
           '// end of file' \
           '#endif'


class TestAspDBTablesGenerator(unittest.TestCase):
    def test_cpp_text(self):
        """
        Доп. проверка инициализации cpp данных, если свалится здесь, то
        нечего особо и проверять дальше

        :return:
        """
        aspf = asp_db_cpp.AspDBCppFile(cpp_text)
        aspf.init_structs()
        self.assertEqual(len(aspf.cpp_structs), 2)
        if len(aspf.cpp_structs) == 2:
            self.assertEqual(aspf.cpp_structs[0].name, 'test')
            self.assertEqual(aspf.cpp_structs[1].name, 'test2')
            # pk
            self.assertEqual(aspf.cpp_structs[1].primary_key, ['id', 'fid'])
            # fk field 0
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].field.asp_type, 'bigint')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].field.asp_name, 'fid')
            self.assertFalse(aspf.cpp_structs[1].foreign_refs[0].field.not_null)
            self.assertFalse(aspf.cpp_structs[1].foreign_refs[0].field.is_array)
            # fk ref 0
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].ref.name, 'fid')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].ref.ftable, 'test')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].ref.ftable_pk, 'id')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].ref.on_update,
                             asp_db_cpp.AspDBRefAction.CASCADE)
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[0].ref.on_delete,
                             asp_db_cpp.AspDBRefAction.SET_NULL)

            # fk field 1
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].field.asp_type, 'bigint')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].field.asp_name, 'ffid')
            self.assertFalse(aspf.cpp_structs[1].foreign_refs[1].field.not_null)
            self.assertFalse(aspf.cpp_structs[1].foreign_refs[1].field.is_array)
            # fk ref 1
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].ref.name, 'ffid')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].ref.ftable, 'ftest')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].ref.ftable_pk, 'id')
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].ref.on_update,
                             asp_db_cpp.AspDBRefAction.CASCADE)
            self.assertEqual(aspf.cpp_structs[1].foreign_refs[1].ref.on_delete,
                             asp_db_cpp.AspDBRefAction.CASCADE)

    def test_aspdb_table_text(self):
        aspf = asp_db_cpp.AspDBCppFile(cpp_text)
        aspf.init_structs()
        # first table
        tt = asp_db_tg.AspDBTableText(aspf.cpp_structs[0])
        self.assertEqual(tt.flags_enum.name, 'flags_' + aspf.cpp_structs[0].get_name())
        self.assertEqual(len(tt.flags_enum.fields), 3)
        self.assertEqual(tt.flags_enum.fields[0], ['f_id', 0x01])
        self.assertEqual(tt.flags_enum.fields[1], ['f_name', 0x02])
        self.assertEqual(tt.flags_enum.fields[2], ['f_full', 0x03])
        # second table
        td = asp_db_tg.AspDBTableText(aspf.cpp_structs[1])
        self.assertEqual(td.flags_enum.name, 'flags_' + aspf.cpp_structs[1].get_name())
        self.assertEqual(len(td.flags_enum.fields), 4)
        self.assertEqual(td.flags_enum.fields[0], ['f_id', 0x01])
        self.assertEqual(td.flags_enum.fields[1], ['f_fid', 0x02])
        self.assertEqual(td.flags_enum.fields[2], ['f_ffid', 0x04])
        self.assertEqual(td.flags_enum.fields[3], ['f_full', 0x07])
        print(td.enum_as_text())

    def test_cpp_gen(self):
        cpp_file = 'tmpfile_table_test.h'
        cpp_module = cpp_file[:-2]
        with open(cpp_file, 'w') as f:
            f.write(cpp_text)
            f.close()
        if os.path.exists(cpp_file):
            # распарсить хэдер
            gen = asp_db_tg.AspDBTablesGenerator(cpp_file)
            print('Create module: ' + cpp_module)
            self.assertEqual(gen.module_name, cpp_module)
            # инициализировать структуры данных
            #   проверить структуру данных
            #   тест AspDBTableText
            raise Exception
        else:
            self.assertTrue(False)
        raise Exception
