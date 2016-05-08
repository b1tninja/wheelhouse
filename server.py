import json
import uuid
import zipapp
from hashlib import sha256
from io import BytesIO


class WheelhouseServer:
    # >> > sha256(b'wheel.reinvent()').hexdigest()
    SHARED_SECRET = '0e65b8de3cdefeb823d155a850a2d3a086d6c798e90e8066153798cd15858768'

    def __init__(self):
        self.clients = {}

    def get_package(self, name):
        # if isinstance(source, types.ModuleType):
        #     source = os.path.dirname(source.__file__)
        if name:
            target = BytesIO()
            try:
                zipapp.create_archive('wheels/' + name, target=target)
            except zipapp.ZipAppError:
                pass
            else:
                # TODO: hash and cache?
                return target.getbuffer()

    def generate_token(self, client_id, challenge):
        return sha256(self.SHARED_SECRET + client_id + challenge)

    def register(self, client_id, challenge):
        if client_id not in self.clients:
            self.clients[client_id] = self.generate_token(client_id, challenge)
            return json.dumps([self.clients[client_id]])

    def get_tasks(client_token):
        # TODO: client authentication
        return json.dumps([(str(uuid.uuid4()), 'test', [], {})])
