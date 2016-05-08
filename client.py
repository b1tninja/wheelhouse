import imp
import json
import os
from datetime import datetime
from uuid import uuid1

# from zipimport import zipimporter
import multiprocessing
# import runpy
import sys
import traceback

from zipfile import ZipFile

from server import WheelhouseServer

from io import BytesIO

class Process(multiprocessing.Process):
    # Saw this on stackoverflow
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pconn, self._cconn = multiprocessing.Pipe()
        self._exception = None

    def run(self):
        try:
            super().run()  # starts target in seperate process
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))
            # raise e  # You can still rise this exception if you need to

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception


class WheelSource(imp.SourcelessFileLoader):
    def __init__(self, source, fullname, path=None):
        self.name = fullname
        self.path = path if path is not None else '<wheels://%s>' % fullname
        self._code = compile(source, self.path, 'exec', flags=0, dont_inherit=True, optimize=2)
        # flags control the future!
        # 'exec' if source consists of a sequence of statements,
        # 'eval' if it consists of a single expression, or
        # 'single' if it consists of a single interactive statement

        # 0 (no optimizatioThe mode argument specifies what kind of code must be compiled;
        # 1 (asserts are removed, __debug__ is false) or
        # 2 (docstrings are removed too).

        super().__init__(fullname, self.path)


class WheelLoader:  # (zipimport.zipimporter):
    COMPILER_OPTIMIZATION_LEVEL = 2
    COMPILER_DONT_INHERIT = True
    COMPILER_FLAGS = 0
    COMPILER_MODE = 'exec'

    def __init__(self, file, name=None, pwd=None):
        if name is None:
            name = '<unknown>'
        self.archive = 'wheel://%s' % name
        # self.prefix = prefix if prefix else ''
        self.zip = ZipFile(file)

        self._files = {}

        self.pwd = pwd

        for filename in self.zip.namelist():
            #     ext = filename.rpartition('.')[-1]
            #     if ext == 'py':
            #         self._code[filename] = compile(self.get_data(filename), self.archive + os.path.sep + self.prefix + subname,
            #                                        self.COMPILER_MODE, flags=self.COMPILER_FLAGS,
            #                                        dont_inherit=self.COMPILER_DONT_INHERIT,
            #                                        optimize=self.COMPILER_OPTIMIZATION_LEVEL)
            #
            #     elif ext in ['pyc', 'pyo']:
            #         self._code[filename] = self.get_data(filename)
            self._files[filename] = self.get_info(filename)

    def get_info(self, filename):
        return self.zip.getinfo(filename)

    def make_filename(self, fullname):
        return self.archive + os.path.sep + os.path.sep.join(fullname.split('.'))

    def get_code(self, fullname):
        filename = self.get_filename(fullname)
        if filename:
            ext = filename.rpartition(os.path.extsep)[-1]
            if ext == 'py':
                return compile(self.get_data(filename), self.make_filename(fullname),
                               self.COMPILER_MODE, flags=self.COMPILER_FLAGS,
                               dont_inherit=self.COMPILER_DONT_INHERIT,
                               optimize=self.COMPILER_OPTIMIZATION_LEVEL)
                # TODO: implement pyc/pyo/pyd/pyz?
                # if ext in ['pyc','pyo']:
                #     pass

    def get_data(self, pathname):
        if pathname in self._files:
            return self.zip.open(pathname, pwd=self.pwd).read()

    @staticmethod
    def get_subname(fullname):
        return fullname.rpartition('.')[-1]

    def get_filename(self, fullname):
        # only the subname is used by zipimporter ?
        subname = self.get_subname(fullname)
        for ext in ['pyc', 'pyo', 'py']:
            filepath = subname + '.' + ext
            if filepath in self._files:
                return filepath
        raise ImportError

    def get_source(self, fullname):
        filename = self.get_filename(fullname)
        return self.get_data(filename)

    def load_module(self, fullname):
        code = self.get_code(fullname)
        # TODO: implement ispkg
        # ispkg = self.is_package(fullname)
        ispkg = True
        # mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
        mod = imp.new_module(fullname)
        mod.__file__ = "<%s>" % self.__class__.__name__
        mod.__loader__ = self
        if ispkg:
            mod.__path__ = []
            mod.__package__ = fullname
        else:
            mod.__package__ = fullname.rpartition('.')[0]
        exec(code, mod.__dict__)
        return mod


# class WheelLoader(imp.SourcelessFileLoader):
#     def __init__(self, buffer, prefix=None, pwd=None):
#
#         for name in self.archive.namelist():
#             assert isinstance(name, str)
#             ext = name.rpartition('.')
#             loaders = {'py': WheelSource}
#             if ext in loaders:
#                 data = self.archive.open(name, pwd=pwd).read()
#                 self.load_module()
#                 self._files
#                 loaders[ext]()
#             else:
#                 print(name)
#
#         for name in names:
#             print(self.zip.getinfo(name))
#
#     def get_code(self, fullname):
#         try:
#             code = compile(self.get_source(fullname), '<string>', 'exec')  # uses current features (futures)
#         except SyntaxError:
#             pass
#         except TypeError:
#             pass  # null bytes?
#         else:
#             return code
#
#     def get_source(self, fullname):
#         return "print('hello world')"
#
#     def is_package(self, fullname):
#         return False
#
#     def load_module(self, fullname):
#         print("Loading wheel", fullname)
#         code = self.get_code(fullname)
#
#         module = sys.modules.setdefault(fullname, imp.new_module(fullname))
#
#         if self.is_package(fullname):
#             module.__path__ = []
#             module.__package__ = fullname
#         else:
#             module.__package__ = fullname.rpartition('.')[0]
#
#         exec(code, module.__dict__)


# class WheelFinder:
#     def __init__(self, wheelhouse):
#         self.wheelhouse = wheelhouse
#
#     def find_module(self, fullname, path=None):
#         pass



# class WheelImporter:
#     basename = 'wheels'
#
#     def __init__(self, wheelhouse):
#         self.wheelhouse = wheelhouse
#
#     def install_meta_hook(self):
#         sys.meta_path.insert(0, self) # finder
#
#     # def install_path_hook(self):
#     #     sys.path_hooks.insert(0, self.factory) # loader factory
#     #
#     # def factory(self, path):
#     #     print(self, path)
#     #     raise ImportError()
#
#     def find_module(self, fullname, path=None):
#         print(self, fullname, path)
#         if fullname.startswith(self.basename):
#             name = fullname.partition('.')[-1]
#             buffer = self.wheelhouse.get_package(name)
#             if buffer:
#                 return WheelLoader(name, BytesIO(buffer))
#
#
#
#
#
# #         # sys.meta_path.insert(0, WheelFinder())
# #         self.wheels = {}
# #         sys.path_hooks.insert(0, self)
# #         # sys.meta_path.insert(0, self)
# #
# #     # File "<frozen importlib._bootstrap>", line 969, in _find_and_load
# #     # File "<frozen importlib._bootstrap>", line 954, in _find_and_load_unlocked
# #     # File "<frozen importlib._bootstrap>", line 896, in _find_spec
# #     # File "<frozen importlib._bootstrap_external>", line 1136, in find_spec
# #     # File "<frozen importlib._bootstrap_external>", line 1107, in _get_spec
# #     # File "<frozen importlib._bootstrap_external>", line 1079, in _path_importer_cache
# #     # File "<frozen importlib._bootstrap_external>", line 1055, in _path_hooks
# #
# #     def find_module(self, fullname, path=None):
# #         print(fullname)
# #         if len(fullname) > 7 and fullname.startswith('wheels.'):
# #             name = fullname[7:]
# #             if name in self.wheels:
# #                 return self.wheels[name]
# #
# #     def add_wheel(self, name, wheel):
# #         # self.wheels.setdefault(name, wheel)
# #         self.wheels[name] = wheel
# #
# #     def import_wheel(self, name):
# #         __import__('wheels.%s' % name)


def WheelRunner(package, *args, **kwargs):
    WheelLoader(package).load_module('wheels.test')

    # pyz, prefix=name)
    # mod = importer.load_module('__init__')
    # importer.add_wheel(name, WheelLoader(pyz))

    # import imp
    # import sys
    # import zlib
    # import imp
    # from importlib.machinery import SourceFileLoader


    # module = imp.new_module(name)
    # module.__file__ = '<wheel>'
    # module.__path__ = []
    # module.__loader__ = SourceFileLoader
    # print(module.__loader__)

    # sys.modules[name] = module
    # print(imp.find_module(name))
    # __import__(name)
    # print(zlib.__loader__)
    # print(zlib.__spec__)
    # print(sys.version)
    print(sys.prefix)
    print(sys.path)
    print(sys.path_hooks)
    print(sys.meta_path)
    print(sys.path_importer_cache)
    print(sys.modules)
    # python 3.4+
    # from importlib.machinery import ModuleSpec, SourceFileLoader
    # test = ModuleSpec(name,loader=SourceFileLoader,is_package=True)
    # import zipimport

    # module = imp.load_module(name, pyz, "%s.pyz" % name, ('pyz', 'rb', imp.PKG_DIRECTORY))
    # print(module)
    # print(sys.modules['test'])
    # _stdout, _stdin = sys.stdout, sys.stdin
    # sys.stdout, sys.stdin = [self.stdout, self.stdin]
    # globals = runpy.run_module(module.__name__, init_globals={}, alter_sys=True)
    # print(globals)
    # sys.stdout, sys.stdin = _stdout, _stdin


class WheelProcess(multiprocessing.Process):
    def __init__(self, package):
        self.package = package

    def target(self, *args, **kwargs):
        # runs in seperate process
        pyz = BytesIO(self.package)
        wheel = WheelLoader(pyz).load_module('__main__')

    def run(self, *args, **kwargs):
        try:
            p = Process(target=self.target, args=args, kwargs=kwargs)
            p.start()
            p.join()

            if p.exception:
                error, traceback = p.exception
                print(error, traceback)
        except Exception as e:
            print(e)
            print(e, traceback.format_exc())


class WheelUnavailable(Exception):
    pass


class Task:
    def __init__(self, task_id, wheel, args, kwargs):
        self.task_id = task_id
        self.wheel = wheel
        self.args = args
        self.kwargs = kwargs


class WheelhouseClient:
    TIMEOUT = 900

    # psk = '0e65b8de3cdefeb823d155a850a2d3a086d6c798e90e8066153798cd15858768'

    def __init__(self, urls):
        assert isinstance(urls, list)
        self.urls = urls
        self.exceptions = []
        self.client_id = str(uuid1())
        # self.pool = multiprocessing.Pool(maxtasksperchild=1)
        self.server = WheelhouseServer()  # TODO: implement netcode
        self.token = None

    def get_tasks(self):
        # TODO: real net code
        response = self.server.get_tasks()
        if response:
            for task in json.loads(response):
                yield Task(*task)

    def get_package(self, name):
        return self.server.get_package(name)

    def log_exception(self, exception):
        self.exceptions.append((datetime.utcnow(), exception))

    def exec_task(self, task):
        assert isinstance(task, Task)
        package = self.get_package(task.wheel)
        if package:
            WheelProcess(package).run(*task.args, **task.kwargs)
        else:
            raise WheelUnavailable(task.wheel)

    def save_result(self, task_id, result):
        print(self, task_id, result)

    # def compute_challenge(self, client_id):
    #     return sha256((self.psk + client_id).encode('ascii')).hexdigest()
    #
    # def register(self, url):
    #     # TODO: implement netcode
    #     (token, challenge_response) = self.server.register(self.client_id, self.compute_challenge(self.client_id))
    #     if self.compute_challenge(challenge_response) == self.psk:
    #         self.token = token
    #     else:
    #         raise Exception('Server failed to authenticate')

    def run_forever(self):
        while True:
            # for url in self.urls:
            #     try:
            #         self.register(url)
            #     except Exception as exception:
            #         self.log_exception(exception)
            #         continue
            #     else:
            #         try:
            # TODO: use pool
            # self.pool.map_async(partial(self.save_result, task.task_id))
            for task in self.get_tasks():
                self.exec_task(task)
                #         except Exception as e:
                #             self.log_exception(e)
                #         break
                # else:
                #     sleep(self.TIMEOUT)


if __name__ == '__main__':
    WheelhouseClient(['localhost']).run_forever()
