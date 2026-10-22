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



from robot.api.deco import keyword

@keyword("summarize-library")
def summarize_library(library):
    # Generated 2026-10-21: Summarize library stats: total books, available books, borrowed books.
    total = len(library.books)
    available = library.available_book()
    borrowed = library.borrowed_book()
    return {"total_books": total, "available_books": available, "borrowed_books": borrowed}
