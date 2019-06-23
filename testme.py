from typing import Optional

from typeit.sums import SumType


from typeit.sums import SumType

class Payment(SumType):
    class Cash:
        amount: str

    class Card:
        amount: str
        card: str


x = Payment.Cash(amount='1')

def process(payment: Payment) -> Optional[str]:
    if isinstance(payment, Payment.Card):
        return payment.card
    return None

z = process(x)