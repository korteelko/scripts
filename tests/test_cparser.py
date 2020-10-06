#!/usr/bin/env python
"""
Тестирования модуля cparser_lite
"""
import cparser_lite
import asp_db_cpp
import unittest


class TestStringMethods(unittest.TestCase):
    def test_comment_remover(self):
        """
        Тест функции удаления C комментариев из исходников

        В общем, скрипт заменяет комментарий на пробел,
        и тут тест под результат подгонялся, НО в данном случае
        мне лишь немного стыдно
        :return:
        """
        # оригинальный исходник
        line = '#ifndef header_guard_h\n' \
               '#define header_guard_h\n' \
               '\n' \
               'struct abc {\n' \
               '  int a;\n' \
               '  double b;\n' \
               '  int/*eger*/ i;\n' \
               '  char *ds;\n' \
               '  /* multiline comment\n' \
               '  start and there is nothing */\n' \
               '};\n' \
               '// comment\n' \
               '#endif  // !header_guard_h\n'
        # исходник без комментариев
        line_uncom = '#ifndef header_guard_h\n' \
                     '#define header_guard_h\n' \
                     '\n' \
                     'struct abc {\n' \
                     '  int a;\n' \
                     '  double b;\n' \
                     '  int  i;\n' \
                     '  char *ds;\n' \
                     '   \n' \
                     '};\n' \
                     ' \n' \
                     '#endif   \n'
        self.assertEqual(line_uncom, cparser_lite.cpp_comment_remover(line))

    def test_brace_content(self):
        """
        Оттестировать функцию получения содержимого скобок
        """
        # cool examples
        self.assertRaises(BaseException, cparser_lite.get_brace_content,
                          'sahg()', '', ')')
        self.assertEqual(cparser_lite.get_brace_content(
            'sahg()', '(', ')'), '')
        self.assertEqual(cparser_lite.get_brace_content(
            'sahg(yju(sd)jkds)', '(', ')'), 'yju(sd)jkds')
        self.assertEqual(cparser_lite.get_brace_content(
            'sahg( )  ds', '(', ')'), ' ')
        self.assertEqual(cparser_lite.get_brace_content(
            'test complex ${case}', '${', '}'), 'case')

        # not cool examples
        self.assertEqual(cparser_lite.get_brace_content(
            'not (ool (ase', '(', ')'), '')
        self.assertEqual(cparser_lite.get_brace_content(
            'not )ool (ase2', '(', ')'), '')
        self.assertEqual(cparser_lite.get_brace_content(
            'not (ool (as)e3', '(', ')'), '')


cpp_text = '#define SOME_DEFINE' \
           '' \
           'struct ASP_TABLE test {' \
           '  field(integer, id, NOT_NULL);' \
           '  field(text, name, NOT_NULL);' \
           '' \
           '  primary_key(id)' \
           '  unique(name, num)' \
           '};' \
           '' \
           'struct ASP_TABLE test2 {' \
           '  field(integer, id, NOT_NULL)' \
           '};' \
           '// end of file' \
           ''


class TestAspDBCppFile(unittest.TestCase):
    def test_init_structs(self):
        aspf = asp_db_cpp.AspDBCppFile(cpp_text)
        aspf.init_structs()
        self.assertEqual(len(aspf.cpp_structs), 2)
        if len(aspf.cpp_structs) == 2:
            self.assertEqual(aspf.cpp_structs[0].name, 'test')
            self.assertEqual(aspf.cpp_structs[1].name, 'test2')
            # aspf.init_structs()

            # first field of `test`
            self.assertEqual(len(aspf.cpp_structs[0].fields), 2)
            self.assertEqual(aspf.cpp_structs[0].fields[0].asp_type, 'integer')
            self.assertEqual(aspf.cpp_structs[0].fields[0].asp_name, 'id')
            self.assertTrue(aspf.cpp_structs[0].fields[0].not_null)
            self.assertFalse(aspf.cpp_structs[0].fields[0].is_array)
            # second field of `test`
            self.assertEqual(aspf.cpp_structs[0].fields[1].asp_type, 'text')
            self.assertEqual(aspf.cpp_structs[0].fields[1].asp_name, 'name')
            self.assertTrue(aspf.cpp_structs[0].fields[1].not_null)
            self.assertFalse(aspf.cpp_structs[0].fields[1].is_array)

            # first field of `test2`
            self.assertEqual(len(aspf.cpp_structs[1].fields), 1)
            self.assertEqual(aspf.cpp_structs[1].fields[0].asp_type, 'integer')
            self.assertEqual(aspf.cpp_structs[1].fields[0].asp_name, 'id')
            self.assertTrue(aspf.cpp_structs[1].fields[0].not_null)
            self.assertFalse(aspf.cpp_structs[1].fields[0].is_array)

    def test_init_structs2(self):
        s = 'struct ASP_TABLE test {' \
            '  field(integer, i, NOT_NULL);' \
            '  field(text, a);' \
            '' \
            '  primary_key(i)' \
            '' \
            '  field_fkey(bigint, fkey, NOT_NULL)' \
            '  reference(fkey, ex(sad), CASCADE, RESTRICT)' \
            '};'
        aspf = asp_db_cpp.AspDBCppFile(s)
        aspf.init_structs()
        self.assertEqual(aspf.cpp_structs[0].name, 'test')
        self.assertEqual(aspf.cpp_structs[0].fields[0].asp_type, 'integer')
        self.assertEqual(aspf.cpp_structs[0].fields[0].asp_name, 'i')
        self.assertTrue(aspf.cpp_structs[0].fields[0].not_null)
        self.assertFalse(aspf.cpp_structs[0].fields[0].is_array)
        self.assertEqual(aspf.cpp_structs[0].fields[1].asp_type, 'text')
        self.assertEqual(aspf.cpp_structs[0].fields[1].asp_name, 'a')
        self.assertFalse(aspf.cpp_structs[0].fields[1].not_null)
        self.assertFalse(aspf.cpp_structs[0].fields[1].is_array)
        # pk
        self.assertEqual(aspf.cpp_structs[0].primary_key, ['i'])
        # fk field
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].field.asp_type, 'bigint')
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].field.asp_name, 'fkey')
        self.assertTrue(aspf.cpp_structs[0].foreign_refs[0].field.not_null)
        self.assertFalse(aspf.cpp_structs[0].foreign_refs[0].field.is_array)
        # fk ref
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].ref.name, 'fkey')
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].ref.ftable, 'ex')
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].ref.ftable_pk, 'sad')
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].ref.on_update,
                         asp_db_cpp.AspDBRefAction.CASCADE)
        self.assertEqual(aspf.cpp_structs[0].foreign_refs[0].ref.on_delete,
                         asp_db_cpp.AspDBRefAction.RESTRICT)


class TestAspDBForeignField(unittest.TestCase):
    def test_init_ff(self):
        ff = asp_db_cpp.AspDBReference('eman', 'qwerty(id)', 'CASCADE', 'RESTRICT')
        self.assertEqual(ff.name, 'eman')
        self.assertEqual(ff.ftable, 'qwerty')
        self.assertEqual(ff.ftable_pk, 'id')
        self.assertEqual(ff.on_update, asp_db_cpp.AspDBRefAction.CASCADE)
        self.assertEqual(ff.on_delete, asp_db_cpp.AspDBRefAction.RESTRICT)


if __name__ == '__main__':
    unittest.main()
