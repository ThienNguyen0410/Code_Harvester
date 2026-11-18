from robot.api.deco import keyword
from typing import List

class Library:
    def __init__(self, books: List[str]):
        self.available = 5
        self.borrow = 5
        self.books = ["Ilove you", "Mrs. Nu's House", "Youth"]

    @keyword("return-available")
    def available_book(self):
        return self.available
    
    @keyword("return-borrowed-book")
    def borrowed_book(self):
        return self.borrow


@keyword("summarize-inventory")
def summarize_inventory(library):
    # Generated on 2026-10-22: Summarize library inventory counts.
    total = len(library.books)
    available = library.available_book()
    borrowed = library.borrowed_book()
    return {"total": total, "available": available, "borrowed": borrowed}
