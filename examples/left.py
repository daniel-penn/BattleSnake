from api import *


class MyBot(CodeBattlesBot):
    def run(self) -> None:
        self.context.set_direction("L")

    def setup(self) -> None:
        return
