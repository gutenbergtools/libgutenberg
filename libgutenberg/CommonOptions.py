# options is a "Borg" set by optparse (note that it's not thread-safe)
class Options:
    __shared_state = {}
    def __init__(self):
        self.__dict__ = self.__shared_state
        
    def update(self, _dict):
        self.__dict__.update(_dict)

options = Options()
