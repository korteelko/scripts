"""
Модуль парсинга и генерации С файлов
"""
import re


def cpp_comment_remover(text):
    """
    Убрать комментарии из C/C++ файлов

    :param text: С/С++ исходники
    :return: Исходники без комментариев
    :TODO Replace to separated file
    """
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            # note: a space and not an empty string
            return " "
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)


def get_brace_content(text, open_brace, close_brace):
    """
    Выделить в тексте `text` кусок текста заключённый между
    первым элементом `open_brace` и парным ему `close_brace`

    :param text: Текс
    :param open_brace: Открывающая последовательность
    :param close_brace: Закрывающая последовательность
    :return: Часть текста между `open_brace` и `close_brace`
    :raise BaseException
    :TODO Replace to separated file
    """
    type_check = (type(text) == type(open_brace)) and (type(close_brace) == str)
    if not type_check:
        raise BaseException('Function `get_brace_content` input data type mismatch '
                            'all arguments must be a strings')
    if not open_brace or not close_brace:
        raise BaseException('Function `get_brace_content` get empty patterns for '
                            'open or close brackets')
    if open_brace == close_brace:
        raise BaseException('Function `get_brace_content` get same pattern for '
                            'open and close pattern' + open_brace)
    i_ob = text.find(open_brace)
    result = ''
    if i_ob != -1:
        start = i_ob
        # одна скобка открыта, фиксирурем
        count = 1
        i_cb = text.find(close_brace, i_ob + len(open_brace))
        i_ob = text.find(open_brace, i_ob + len(open_brace))
        while i_cb != -1:
            if (i_cb > i_ob) and (i_ob != -1):
                # ещё одна открывающая скобка
                count += 1
                i_ob = text.find(open_brace, i_ob + len(open_brace))
                continue
            else:
                # сначала закрывающая скобка
                count -= 1
            if count == 0:
                # если всё открытое закрыто - закончили
                result = text[start + len(open_brace): i_cb]
                break
            # прежде была закрывающая скобка, обновим её позицию
            i_cb = text.find(close_brace, i_cb + len(close_brace))
    return result


class ICppFunctions:
    """
    Класс предоставляющий интерфейс инициализации cpp данных
    """
    def init_cpp_structs(self, name, source):
        pass


class CppEnum:
    """
    Cpp представление class enum'а
    """
    def __init__(self, name):
        self.name = name
        self.fields = list()
        self.nums = set()

    def try_add_field(self, name, num):
        """
        Добавить параметр к enum

        :param name: Имя параметра
        :param num: Номер параметра
        :return: True если значение добавлено
                 False иначе
        """
        if num not in self.nums:
            self.fields.append([name, num])
        else:
            raise Exception('Number ' + str(num) + ' already in use')


class CppStructs:
    """
    Cpp структура данных
    """
    def __init__(self, name, source):
        """
        Инициализировать структуру
        :param name: Имя её
        :param source: Контент, без комментариев, от скобки до скобки
        """
        self.name = name
        self.source = source
        # поля структуры
        self.fields = list()

    def get_name(self):
        return self.name

    def init_data(self):
        pass


class CppFile:
    """
    Python инициализатор структур и классов C++
    TODO: не работать с оригинальным, свободным форматом - удалить все
        комментарии, лишние пробелы, переводы строк
    """
    def __init__(self, text, cpp_functions):
        """
        Инициализировать
        C + + структуру
        """
        # Функции инициализаци cpp данных
        self.cpp_functions = cpp_functions
        # Сразу отбросить комментарии из текста
        self.source = cpp_comment_remover(text)
        # Регулярное выражение на инициализацию структур
        self.regex_struct_st = r'struct\s' + self.get_class_marker() + r'\s[a-zA-Z]{1}\w*[\s]*{'

        # контейнеры
        self.cpp_structs = list()

    def get_class_marker(self):
        """
        Поолучить название маркера обрабатываемых данных.
        Т.е. cpp файле, на структуры и классы прописывается
        какой-то пустой дефайн, в результате чего они выглядят так:
            struct MARKER_EXAMPLE marker_holder { ... };
        Вот, найдя MARKER_HOLDER в таком cpp, будем от него плясать

        :return: Строка маркер
        """
        # ? pycharm мне тут варнинг прокидывал на простой 'pass'
        #   когда я его из init вызывал
        return ''

    def init_structs(self):
        """
        Инициализировать cpp структуры, записать объекты
        в лист self.cpp_structs

        :return: Nothing
        """
        structs = re.findall(self.regex_struct_st, self.source)
        missed = list()
        for struct in structs:
            # по результату применения регулярных выражений
            #   найдём позицию объявлений структур
            struct_pos = self.source.find(struct)
            if struct_pos == -1:
                missed.append(struct + ' ~~ cannot find position this string position '
                                       'in cpp source file.')
                continue
            name = self.get_class_name(struct)
            if not name:
                missed.append(struct + ' ~~ cannot get name of this struct')
            source = get_brace_content(self.source[struct_pos:], '{', '}')
            if not source:
                missed.append(struct + ' ~~ cannot get brace content of struct')
            # всё(или не всё нашли, продолжим инициализацию данных)
            if len(missed) > 0:
                print('Warning: Some algorithm CppFile finished with errors')
                print(missed)
            self.cpp_structs.append(self.cpp_functions.init_cpp_structs(name, source))

    def get_class_name(self, head_str):
        """
        Вытащить из инициализирующей строки структуры её имя
        :param head_str: инициализирующая строка
        :return: имя  структуры
        :TODO решение очень плохое
        """
        # убрать маркер из строки
        head_str = head_str.replace(self.get_class_marker(), '')
        head_str = head_str.replace('struct', '')
        head_str = head_str.replace('class', '')
        head_str = head_str.replace('{', '')
        return head_str.strip()

