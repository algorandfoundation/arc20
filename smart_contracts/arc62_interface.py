from abc import ABC, abstractmethod

from algopy import ARC4Contract, UInt64, arc4


class Arc62Interface(ARC4Contract, ABC):
    """
    ARC-0062 (ASA Circulating Supply) - Interface
    """

    @abstractmethod
    @arc4.abimethod(readonly=True)
    def arc62_get_circulating_supply(self, asset_id: UInt64) -> UInt64:
        pass
