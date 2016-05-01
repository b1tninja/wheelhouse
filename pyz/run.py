import os
import zipapp
from io import BytesIO

#from pathlib import Path
#from types import ModuleType

def package(source):
    # if isinstance(source, ModuleType):
    #     source = os.path.dirname(source.__file__)
    target = BytesIO()
    zipapp.create_archive(source, target=target)
    # target.getbuffer()
    return target
    # TODO: hash and cache? compile?



import multiprocessing
import traceback

class Process(multiprocessing.Process):
    # Saw this on stackoverflow
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pconn, self._cconn = multiprocessing.Pipe()
        self._exception = None

    def run(self):
        try:
            super().run()
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


def target(name, pyz):
    import imp
    import sys
    import runpy
    import io
    module = imp.load_module(name,pyz,name, ('pyz', 'rb', imp.PKG_DIRECTORY))
    print(module)
    print(sys.modules['test'])
    # _stdout, _stdin = sys.stdout, sys.stdin
    # sys.stdout, sys.stdin = [self.stdout, self.stdin]
    secret_variable=True
    runpy.run_module(module.__name__, init_globals={}, alter_sys=True)
    # sys.stdout, sys.stdin = _stdout, _stdin


pkg = 'test'
pyz = package(os.path.realpath(pkg))
p = Process(target = target, args=[pkg, pyz])
p.start()
p.join()

if p.exception:
    error, traceback = p.exception
    print(error, traceback)